"""Auto Trade Scheduler - 后端计划任务统一调度

替代原来每个任务独立 asyncio.Task 的模式，
改为单一后台调度器统一轮询所有已启用任务，
所有运行时状态持久化到 SQLite，服务重启后自动恢复。
"""
import asyncio
import logging
from datetime import datetime

from backend.models.auto_trade import AutoTradeTask
from backend.models.settings import SimSettings
from backend.services import simulation_trade as st
from backend.services import gold_data
from backend.services import grid_trade

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL = 30


class AutoTradeScheduler:
    _task: asyncio.Task = None
    _running: bool = False
    _check_interval: int = DEFAULT_CHECK_INTERVAL

    @classmethod
    def is_running(cls) -> bool:
        return cls._running and cls._task is not None and not cls._task.done()

    @classmethod
    async def start(cls, check_interval: int = None):
        if cls.is_running():
            logger.warning("AutoTradeScheduler 已在运行中")
            return

        if check_interval is not None:
            cls._check_interval = check_interval

        cls._running = True
        cls._task = asyncio.create_task(cls._run_loop())
        logger.info(f"AutoTradeScheduler 已启动，检查间隔: {cls._check_interval}s")

    @classmethod
    async def stop(cls):
        cls._running = False
        if cls._task and not cls._task.done():
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
        cls._task = None
        logger.info("AutoTradeScheduler 已停止")

    @classmethod
    async def _run_loop(cls):
        while cls._running:
            try:
                await cls._check_all_tasks()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"AutoTradeScheduler 循环异常: {e}")

            await asyncio.sleep(cls._check_interval)

    @classmethod
    async def _check_all_tasks(cls):
        if not cls._is_trading_time():
            return

        try:
            all_tasks = AutoTradeTask.find_all_enabled()
        except Exception as e:
            logger.error(f"查询已启用任务失败: {e}")
            return

        if not all_tasks:
            return

        for task_cfg in all_tasks:
            try:
                await cls._check_and_trade(task_cfg)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                user_id = task_cfg.get("user_id", "?")
                symbol = task_cfg.get("symbol", "?")
                logger.error(f"[AutoTradeScheduler] {user_id}/{symbol} 检查异常: {e}")

    @classmethod
    def _is_trading_time(cls) -> bool:
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        hour, minute = now.hour, now.minute
        if (hour == 9 and minute >= 30) or (9 < hour < 11) or (hour == 11 and minute <= 30):
            return True
        if (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
            return True
        return False

    @classmethod
    async def _check_and_trade(cls, task_cfg: dict) -> None:
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]

        grid_count = task_cfg.get("grid_count", 10)
        grid_spread = task_cfg.get("grid_spread", 0.10)
        base_ma_key = task_cfg.get("base_ma_key", "MA20")
        macd_ma_key = task_cfg.get("macd_ma_key")
        position_size = task_cfg.get("position_size", 1.0)

        df = gold_data.get_full_data(symbol, datalen=90)
        if df is None or len(df) < 20:
            return

        latest = df.iloc[-1]

        macd_hist_mean = None
        if macd_ma_key:
            window = 20
            macd_hist_mean = df["MACD_HIST"].iloc[-window:].mean() if len(df) >= window else df["MACD_HIST"].mean()

        signal = grid_trade.get_grid_signal(
            latest,
            grid_count=grid_count,
            grid_spread=grid_spread,
            ma_key=base_ma_key,
            macd_ma_key=macd_ma_key,
            macd_hist_mean=macd_hist_mean,
        )

        AutoTradeTask.update_last_check(user_id, symbol, signal.get("signal"))

        close = float(latest["收盘"])

        # 更新浮动盈亏
        task_cash = task_cfg.get("task_cash", task_cfg.get("allocated_funds", 0))
        task_pnl = task_cfg.get("task_pnl", 0)
        cur_shares = task_cfg.get("position_shares", 0)
        cur_avg_cost = task_cfg.get("position_avg_cost", 0)
        unrealized = (close - cur_avg_cost) * cur_shares if cur_shares > 0 else 0
        task_name = task_cfg.get("task_name", symbol)

        AutoTradeTask.update_runtime(
            user_id, symbol,
            task_cash=task_cash,
            task_pnl=task_pnl,
            position_shares=cur_shares,
            position_avg_cost=cur_avg_cost,
            unrealized_pnl=unrealized,
            task_name=task_name,
        )

        if signal["signal"] not in ("买入", "卖出"):
            return

        trade_name = latest.get("名称", symbol)
        if not trade_name or trade_name == symbol:
            trade_name = symbol

        position_ratio = signal.get("position_ratio", 0.5)
        allocated_funds = task_cfg.get("allocated_funds", 0)
        target_market_value = allocated_funds * position_ratio
        current_market_value = cur_shares * close
        value_diff = target_market_value - current_market_value

        settings = SimSettings.get(symbol)
        commission_rate = settings.get("commission_rate", 0.0003)
        min_commission = settings.get("min_commission", 5.0)
        stamp_tax_rate = settings.get("stamp_tax_rate", 0.001)
        transfer_fee_rate = settings.get("transfer_fee_rate", 0.00002)

        step_value = close * (signal.get("step_pct", 1.0) / 100) * 100
        if abs(value_diff) < step_value:
            return

        if value_diff > 0:
            buy_amount = value_diff
            shares = int(round(buy_amount / close / 100)) * 100
            if shares < 100:
                return
            amount = close * shares
            commission_est = max(amount * commission_rate, min_commission)
            if task_cash < (amount + commission_est):
                return
            task_cash -= (amount + commission_est)
            total_cost = cur_avg_cost * cur_shares + amount
            cur_shares += shares
            cur_avg_cost = total_cost / cur_shares if cur_shares > 0 else close
            result = st.execute_trade(user_id, "buy", symbol, trade_name, close, shares, trade_type="auto")
            action_str = "买入"
        else:
            sell_amount = abs(value_diff)
            shares = int(round(sell_amount / close / 100)) * 100
            if shares < 100 or cur_shares < 100:
                return
            shares = min(shares, cur_shares)
            shares = (shares // 100) * 100
            if shares < 100:
                return
            result = st.execute_trade(user_id, "sell", symbol, trade_name, close, shares, trade_type="auto")
            if result.get("success"):
                sell_proceeds = close * shares
                stamp_tax = sell_proceeds * stamp_tax_rate
                transfer_fee = sell_proceeds * transfer_fee_rate if symbol.startswith("sh") else 0
                net_proceeds = sell_proceeds - max(sell_proceeds * commission_rate, min_commission) - stamp_tax - transfer_fee
                task_cash += net_proceeds
                pnl = (close - cur_avg_cost) * shares
                task_pnl += pnl
                cur_shares -= shares
                if cur_shares == 0:
                    cur_avg_cost = 0
            action_str = "卖出"

        if result.get("success"):
            logger.info(f"[AutoTradeScheduler] {user_id}/{symbol} {action_str} {shares} shares at {close:.4f}, target_ratio={position_ratio:.2f}, diff={value_diff:.2f}")
            AutoTradeTask.update_runtime(
                user_id, symbol,
                task_cash=task_cash,
                task_pnl=task_pnl,
                position_shares=cur_shares,
                position_avg_cost=cur_avg_cost,
                task_name=trade_name,
            )

    @classmethod
    def get_status(cls, user_id: int, symbol: str = None):
        """获取任务运行状态（供 API 查询用）"""
        if symbol:
            task_cfg = AutoTradeTask.find_by_symbol(user_id, symbol)
            if not task_cfg:
                return None
            return {
                "symbol": task_cfg["symbol"],
                "running": cls.is_running() and task_cfg.get("enabled", False),
                "task": task_cfg,
                "task_cash": task_cfg.get("task_cash", task_cfg.get("allocated_funds", 0)),
                "task_pnl": task_cfg.get("task_pnl", 0),
                "task_position": {
                    "shares": task_cfg.get("position_shares", 0),
                    "avg_cost": task_cfg.get("position_avg_cost", 0),
                },
                "task_name": task_cfg.get("task_name", symbol),
                "unrealized_pnl": task_cfg.get("unrealized_pnl", 0),
            }

        tasks = AutoTradeTask.find_by_user(user_id)
        result = []
        for t in tasks:
            result.append({
                "symbol": t["symbol"],
                "running": cls.is_running() and t.get("enabled", False),
                "task": t,
                "task_cash": t.get("task_cash", t.get("allocated_funds", 0)),
                "task_pnl": t.get("task_pnl", 0),
                "task_position": {
                    "shares": t.get("position_shares", 0),
                    "avg_cost": t.get("position_avg_cost", 0),
                },
                "task_name": t.get("task_name", t.get("symbol", "")),
                "unrealized_pnl": t.get("unrealized_pnl", 0),
            })
        return result
