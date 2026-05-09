"""Auto Trade Scheduler - 后端计划任务统一调度

替代原来每个任务独立 asyncio.Task 的模式，
改为单一后台调度器统一轮询所有已启用任务，
所有运行时状态持久化到 PostgreSQL，服务重启后自动恢复。
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
CONSECUTIVE_SIGNALS_REQUIRED = 2   # 交易信号需连续 N 次相同才执行
MIN_STEP_VALUE_PCT = 0.02          # 最小调仓阈值：分配资金的 2%


class AutoTradeScheduler:
    _task: asyncio.Task = None
    _running: bool = False
    _check_interval: int = DEFAULT_CHECK_INTERVAL
    _next_interval: int = DEFAULT_CHECK_INTERVAL

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

            await asyncio.sleep(cls._next_interval)

    @classmethod
    def _calc_dynamic_interval(cls, task_cfg: dict, atr_pct: float) -> int:
        if not task_cfg.get("dynamic_interval", False):
            return cls._check_interval

        config_interval = task_cfg.get("check_interval", 30)

        if atr_pct < 0:
            return config_interval

        if atr_pct >= 2.0:
            base = config_interval // 3
        elif atr_pct >= 1.0:
            base = config_interval // 2
        elif atr_pct >= 0.5:
            base = config_interval
        else:
            base = min(config_interval * 2, 90)

        return max(10, min(base, config_interval))

    @classmethod
    async def _check_all_tasks(cls):
        if not cls._is_trading_time():
            cls._next_interval = cls._check_interval
            return

        try:
            all_tasks = AutoTradeTask.find_all_enabled()
        except Exception as e:
            logger.error(f"查询已启用任务失败: {e}")
            return

        if not all_tasks:
            cls._next_interval = cls._check_interval
            return

        has_dynamic = any(t.get("dynamic_interval", False) for t in all_tasks)
        min_interval = cls._check_interval

        for task_cfg in all_tasks:
            try:
                await cls._check_and_trade(task_cfg)
                if has_dynamic:
                    df = gold_data.get_full_data(task_cfg["symbol"], datalen=30)
                    if df is not None and len(df) >= 5:
                        atr = float(df["ATR"].iloc[-1]) if "ATR" in df.columns else 0
                        close = float(df["收盘"].iloc[-1])
                        atr_pct = atr / close * 100 if close > 0 else -1
                        task_interval = cls._calc_dynamic_interval(task_cfg, atr_pct)
                        min_interval = min(min_interval, task_interval)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                user_id = task_cfg.get("user_id", "?")
                symbol = task_cfg.get("symbol", "?")
                logger.error(f"[AutoTradeScheduler] {user_id}/{symbol} 检查异常: {e}")

        cls._next_interval = min_interval if has_dynamic else cls._check_interval

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

        strategy = task_cfg.get("strategy", "grid")
        position_size = task_cfg.get("position_size", 1.0)
        stop_loss_pct = task_cfg.get("stop_loss_pct", -5.0)
        take_profit_pct = task_cfg.get("take_profit_pct", 10.0)
        trend_ma_key = task_cfg.get("trend_ma_key")

        df = gold_data.get_full_data(symbol, datalen=90)
        if df is None or len(df) < 20:
            return

        latest = df.iloc[-1]
        close = float(latest["收盘"])

        task_cash = task_cfg.get("task_cash", task_cfg.get("allocated_funds", 0))
        task_pnl = task_cfg.get("task_pnl", 0)
        cur_shares = task_cfg.get("position_shares", 0)
        cur_avg_cost = task_cfg.get("position_avg_cost", 0)
        unrealized = (close - cur_avg_cost) * cur_shares if cur_shares > 0 else 0
        task_name = task_cfg.get("task_name", symbol)
        allocated_funds = task_cfg.get("allocated_funds", 0)

        # ========== 1. 同步任务资金与模拟账户 ==========
        portfolio = st.get_portfolio(user_id)
        if portfolio and portfolio.get("account"):
            account_cash = float(portfolio["account"].get("cash", 0))
            if account_cash <= 0 and task_cash > 0:
                logger.warning(f"[Sync] {user_id}/{symbol} 模拟账户已无现金，暂停任务")
                AutoTradeTask.update_enabled(user_id, symbol, False)
                return

        # ========== 2. 止损 / 止盈 检查（不受冷却期限制）==========
        if cur_shares > 0 and cur_avg_cost > 0:
            total_pnl_pct = (close - cur_avg_cost) / cur_avg_cost * 100

            if total_pnl_pct <= stop_loss_pct:
                logger.warning(f"[StopLoss] {user_id}/{symbol} 触发止损 ({total_pnl_pct:.1f}% ≤ {stop_loss_pct:.1f}%)")
                await cls._force_close_position(user_id, symbol, close, cur_shares, task_cfg,
                                                f"止损触发 ({total_pnl_pct:.1f}%)", "stop_loss")
                AutoTradeTask.record_trade(user_id, symbol, "sell")
                return

            if total_pnl_pct >= take_profit_pct:
                logger.info(f"[TakeProfit] {user_id}/{symbol} 触发止盈 ({total_pnl_pct:.1f}% ≥ {take_profit_pct:.1f}%)")
                await cls._force_close_position(user_id, symbol, close, cur_shares, task_cfg,
                                                f"止盈触发 ({total_pnl_pct:.1f}%)", "take_profit")
                AutoTradeTask.record_trade(user_id, symbol, "sell")
                return

        # ========== 3. 趋势过滤 ==========
        if trend_ma_key:
            trend_ma = float(latest.get(trend_ma_key, 0))
            if trend_ma > 0:
                trend_above = close > trend_ma
                pct_above = (close - trend_ma) / trend_ma * 100
                logger.debug(f"[TrendFilter] {user_id}/{symbol} close={close:.4f}, {trend_ma_key}={trend_ma:.4f}, above={pct_above:+.2f}%")
            else:
                trend_above = None
        else:
            trend_above = None

        # ========== 4. 策略信号计算 ==========
        if strategy == "ma_trend":
            signal = grid_trade.get_ma_trend_signal(
                latest,
                fast_ma_key=task_cfg.get("base_ma_key", "MA5"),
                slow_ma_key=trend_ma_key or "MA20",
                position_size=position_size,
            )
        else:
            grid_count = task_cfg.get("grid_count", 10)
            grid_spread = task_cfg.get("grid_spread", 0.10)
            base_ma_key = task_cfg.get("base_ma_key", "MA20")
            macd_ma_key = task_cfg.get("macd_ma_key")

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

        # ========== 5. 趋势过滤修正信号 ==========
        if trend_above is not None and signal["signal"] in ("买入", "卖出"):
            if not trend_above and signal["signal"] == "买入":
                logger.info(f"[TrendFilter] {user_id}/{symbol} 价格低于{trend_ma_key}，过滤买入信号")
                signal["signal"] = "观望"
                signal["action_desc"] = f"价格低于{trend_ma_key}，逆势不买入"
            elif trend_above and signal["signal"] == "卖出":
                logger.info(f"[TrendFilter] {user_id}/{symbol} 价格高于{trend_ma_key}，过滤卖出信号")
                signal["signal"] = "观望"
                signal["action_desc"] = f"价格高于{trend_ma_key}，逆势不卖出"

        # ========== 6. 信号一致性确认（连续 N 次相同信号才执行）==========
        signal_confirmed = AutoTradeTask.update_consecutive_signals(
            user_id, symbol, signal["signal"], CONSECUTIVE_SIGNALS_REQUIRED
        )
        AutoTradeTask.update_last_check(user_id, symbol, signal.get("signal"))

        # ========== 7. 更新浮动盈亏 ==========
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

        if not signal_confirmed:
            logger.debug(f"[SignalGuard] {user_id}/{symbol} 信号 '{signal['signal']}' 未连续{CONSECUTIVE_SIGNALS_REQUIRED}次，等待确认")
            return

        # ========== 8. 冷却期检查 ==========
        if AutoTradeTask.is_in_cooldown(user_id, symbol):
            cooldown = task_cfg.get("cooldown_seconds", 60)
            logger.debug(f"[Cooldown] {user_id}/{symbol} 在冷却期内 ({cooldown}s)，跳过交易")
            return

        # ========== 9. 每日交易上限检查 ==========
        if not AutoTradeTask.can_trade_today(user_id, symbol):
            max_trades = task_cfg.get("max_daily_trades", 50)
            logger.warning(f"[DailyLimit] {user_id}/{symbol} 已达今日交易上限 ({max_trades}次)，跳过")
            return

        trade_name = latest.get("名称", symbol)
        if not trade_name or trade_name == symbol:
            trade_name = symbol

        # ========== 10. 计算仓位偏差和调仓数量 ==========
        position_ratio = signal.get("position_ratio", 0.5)

        max_position_ratio = position_size
        effective_ratio = round(min(position_ratio, max_position_ratio), 4)

        target_market_value = allocated_funds * effective_ratio
        current_market_value = cur_shares * close
        value_diff = target_market_value - current_market_value

        current_position_ratio = current_market_value / allocated_funds if allocated_funds > 0 else 0

        POSITION_MATCH_TOLERANCE = 0.03
        if abs(current_position_ratio - effective_ratio) < POSITION_MATCH_TOLERANCE:
            logger.debug(f"[PositionMatch] {user_id}/{symbol} 当前仓位 {current_position_ratio:.2%} ≈ 建议 {effective_ratio:.2%}，无需调仓")
            return

        settings = SimSettings.get(symbol)
        commission_rate = settings.get("commission_rate", 0.0003)
        min_commission = settings.get("min_commission", 5.0)
        stamp_tax_rate = settings.get("stamp_tax_rate", 0.001)
        transfer_fee_rate = settings.get("transfer_fee_rate", 0.00002)

        min_step_value = max(allocated_funds * MIN_STEP_VALUE_PCT, 100 * close)
        if abs(value_diff) < min_step_value:
            logger.debug(f"[StepGuard] {user_id}/{symbol} 仓位偏差金额 {value_diff:.2f} < 最小阈值 {min_step_value:.2f}，跳过")
            return

        # ========== 11. 执行交易 ==========
        if value_diff > 0:
            buy_amount = value_diff
            shares = int(round(buy_amount / close / 100)) * 100
            if shares < 100:
                return
            amount = close * shares
            commission_est = max(amount * commission_rate, min_commission)
            if task_cash < (amount + commission_est):
                logger.warning(f"[CashGuard] {user_id}/{symbol} 任务现金不足 task_cash={task_cash:.2f} < need={amount + commission_est:.2f}")
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
            logger.info(f"[AutoTradeScheduler] {user_id}/{symbol} {action_str} {shares}股 @ {close:.4f}, 建议仓位={effective_ratio:.2%}, 当前仓位={current_position_ratio:.2%}, 偏差={value_diff:.2f}")
            AutoTradeTask.update_runtime(
                user_id, symbol,
                task_cash=task_cash,
                task_pnl=task_pnl,
                position_shares=cur_shares,
                position_avg_cost=cur_avg_cost,
                task_name=trade_name,
            )
            AutoTradeTask.record_trade(user_id, symbol, action_str)

    @classmethod
    async def _force_close_position(cls, user_id, symbol, close, shares, task_cfg, reason, close_type):
        """强制清仓（止损/止盈触发时调用）"""
        if shares < 100:
            return

        shares = (shares // 100) * 100
        if shares < 100:
            return

        trade_name = task_cfg.get("task_name", symbol)
        result = st.execute_trade(user_id, "sell", symbol, trade_name, close, shares, trade_type="auto")

        if result.get("success"):
            settings = SimSettings.get(symbol)
            commission_rate = settings.get("commission_rate", 0.0003)
            min_commission = settings.get("min_commission", 5.0)
            stamp_tax_rate = settings.get("stamp_tax_rate", 0.001)
            transfer_fee_rate = settings.get("transfer_fee_rate", 0.00002)

            sell_proceeds = close * shares
            stamp_tax = sell_proceeds * stamp_tax_rate
            transfer_fee = sell_proceeds * transfer_fee_rate if symbol.startswith("sh") else 0
            net_proceeds = sell_proceeds - max(sell_proceeds * commission_rate, min_commission) - stamp_tax - transfer_fee

            cur_avg_cost = task_cfg.get("position_avg_cost", 0)
            pnl = (close - cur_avg_cost) * shares
            new_cash = task_cfg.get("task_cash", 0) + net_proceeds
            new_pnl = task_cfg.get("task_pnl", 0) + pnl

            AutoTradeTask.update_runtime(
                user_id, symbol,
                task_cash=new_cash,
                task_pnl=new_pnl,
                position_shares=0,
                position_avg_cost=0,
                task_name=task_cfg.get("task_name", symbol),
            )
            logger.warning(f"[{close_type.upper()}] {user_id}/{symbol} 已清仓 {shares}股 @ {close:.4f}, 盈亏={pnl:.2f}, 原因={reason}")
        else:
            logger.error(f"[{close_type.upper()}] {user_id}/{symbol} 清仓失败: {result.get('error', '')}")

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
                "trade_count_today": task_cfg.get("trade_count_today", 0),
                "last_trade_time": task_cfg.get("last_trade_time"),
                "last_trade_direction": task_cfg.get("last_trade_direction"),
                "consecutive_signals": task_cfg.get("consecutive_signals", 0),
                "in_cooldown": AutoTradeTask.is_in_cooldown(task_cfg["user_id"], task_cfg["symbol"]),
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
                "trade_count_today": t.get("trade_count_today", 0),
                "last_trade_time": t.get("last_trade_time"),
                "last_trade_direction": t.get("last_trade_direction"),
                "consecutive_signals": t.get("consecutive_signals", 0),
                "in_cooldown": AutoTradeTask.is_in_cooldown(t["user_id"], t["symbol"]),
            })
        return result
