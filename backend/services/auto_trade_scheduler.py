"""Auto Trade Scheduler - 后端计划任务统一调度

替代原来每个任务独立 asyncio.Task 的模式，
改为单一后台调度器统一轮询所有已启用任务，
所有运行时状态持久化到 PostgreSQL，服务重启后自动恢复。
"""
import asyncio
import logging
from datetime import datetime, timedelta

from typing import Dict, Any, Optional
from backend.models.auto_trade import AutoTradeTask
from backend.models.settings import SimSettings
from backend.services import simulation_trade as st
from backend.services import gold_data
from backend.services import grid_trade
from backend.services.strategies import StrategyFactory
from backend.utils.timezone import china_now_naive

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL = 30
CONSECUTIVE_SIGNALS_REQUIRED = 2   # 交易信号需连续 N 次相同才执行
MIN_STEP_VALUE_PCT = 0.02          # 最小调仓阈值：分配资金的 2%


class AutoTradeScheduler:
    _task: asyncio.Task = None
    _running: bool = False
    _check_interval: int = DEFAULT_CHECK_INTERVAL
    _next_interval: int = DEFAULT_CHECK_INTERVAL
    _data_cache: Dict[str, Any] = {}
    _data_cache_ts: float = 0

    @classmethod
    def is_running(cls) -> bool:
        result = cls._running and cls._task is not None and not cls._task.done()
        logger.debug(f"[Scheduler] is_running() = {result}, _running={cls._running}, _task={cls._task}, done={cls._task.done() if cls._task else 'N/A'}")
        return result

    @classmethod
    async def start(cls, check_interval: int = None):
        if cls.is_running():
            logger.warning("AutoTradeScheduler 已在运行中")
            return

        if check_interval is not None:
            cls._check_interval = check_interval

        cls._running = True
        cls._task = asyncio.create_task(cls._run_loop())
        logger.info(f"[Scheduler] AutoTradeScheduler 已启动，检查间隔: {cls._check_interval}s")
        logger.info(f"[Scheduler] 内部状态: _running={cls._running}, _task={cls._task}, done={cls._task.done() if cls._task else 'N/A'}")

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
        from backend.utils.timezone import get_china_now
        
        logger.info(f"[Scheduler] _run_loop 启动，_running={cls._running}")
        
        while cls._running:
            now = get_china_now()
            logger.info(f"[Scheduler] ========== 开始检查任务 - {now.strftime('%Y-%m-%d %H:%M:%S')} ==========")
            
            try:
                await cls._check_all_tasks()
                logger.info(f"[Scheduler] _check_all_tasks 完成")
            except asyncio.CancelledError:
                logger.warning(f"[Scheduler] _check_all_tasks 被取消")
                raise
            except Exception as e:
                logger.error(f"[Scheduler] _check_all_tasks 异常: {e}")
            
            next_time = get_china_now()
            next_time = next_time.replace(microsecond=0) + timedelta(seconds=cls._next_interval)
            logger.info(f"[Scheduler] 本次检查完成，下次检查时间: {next_time.strftime('%Y-%m-%d %H:%M:%S')} (间隔 {cls._next_interval}s)")
            
            logger.info(f"[Scheduler] 准备 sleep {cls._next_interval} 秒，当前 _running={cls._running}")
            await asyncio.sleep(cls._next_interval)
            logger.info(f"[Scheduler] sleep 完成，即将进入下一轮，当前 _running={cls._running}")
        
        logger.info(f"[Scheduler] _run_loop 退出循环，_running={cls._running}")

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

        return max(10, min(base, 90))

    @classmethod
    async def _check_all_tasks(cls):
        is_trading_time = cls._is_trading_time()
        logger.info(f"[Scheduler] _check_all_tasks 开始: is_trading_time={is_trading_time}")

        try:
            all_tasks = AutoTradeTask.find_all_enabled()
            logger.info(f"[Scheduler] 找到 {len(all_tasks)} 个启用任务")
        except Exception as e:
            logger.error(f"查询已启用任务失败: {e}")
            cls._next_interval = cls._check_interval
            return

        if not all_tasks:
            logger.info(f"[Scheduler] 没有已启用任务")
            cls._next_interval = cls._check_interval
            return

        has_dynamic = any(t.get("dynamic_interval", False) for t in all_tasks)
        min_interval = cls._check_interval
        logger.info(f"[Scheduler] has_dynamic={has_dynamic}, min_interval={min_interval}")

        data_cache: Dict[str, Any] = {}

        for task_cfg in all_tasks:
            symbol = task_cfg["symbol"]
            if symbol not in data_cache:
                try:
                    data_cache[symbol] = gold_data.get_full_data(symbol, datalen=90)
                except Exception as e:
                    logger.warning(f"[Scheduler] 缓存数据获取失败 {symbol}: {e}")
                    data_cache[symbol] = None

        cls._data_cache = data_cache
        import time as _time
        cls._data_cache_ts = _time.time()

        for task_cfg in all_tasks:
            try:
                symbol = task_cfg["symbol"]
                if is_trading_time:
                    await cls._check_and_trade(task_cfg, data_cache)
                    if has_dynamic:
                        df = data_cache.get(symbol)
                        if df is not None and len(df) >= 5:
                            atr = float(df["ATR"].iloc[-1]) if "ATR" in df.columns else 0
                            close = float(df["收盘"].iloc[-1])
                            atr_pct = atr / close * 100 if close > 0 else -1
                            task_interval = cls._calc_dynamic_interval(task_cfg, atr_pct)
                            min_interval = min(min_interval, task_interval)
                            logger.info(f"[Scheduler] 动态间隔计算: atr={atr}, atr_pct={atr_pct}, task_interval={task_interval}")
                else:
                    await cls._update_check_time(task_cfg, data_cache)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                user_id = task_cfg.get("user_id", "?")
                symbol = task_cfg.get("symbol", "?")
                logger.error(f"[AutoTradeScheduler] {user_id}/{symbol} 检查异常: {e}")

        logger.info(f"[Scheduler] _check_all_tasks 结束: 设置 _next_interval={min_interval if has_dynamic else cls._check_interval}")
        cls._next_interval = min_interval if has_dynamic else cls._check_interval

    @classmethod
    async def _update_check_time(cls, task_cfg: dict, data_cache: Dict[str, Any] = None) -> None:
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]
        strategy = task_cfg.get("strategy", "grid")
        try:
            if data_cache and symbol in data_cache:
                df = data_cache[symbol]
            else:
                df = gold_data.get_full_data(symbol, datalen=90)
            if df is not None and len(df) >= 20:
                latest = df.iloc[-1]
                close = float(latest["收盘"])
                try:
                    strategy_obj = StrategyFactory.get(strategy)
                    signal = strategy_obj.calc_signal(latest, df, task_cfg)
                except ValueError:
                    if strategy == "ma_trend":
                        signal = grid_trade.get_ma_trend_signal(
                            latest,
                            fast_ma_key=task_cfg.get("base_ma_key", "MA5"),
                            slow_ma_key=task_cfg.get("trend_ma_key") or "MA20",
                            position_size=task_cfg.get("position_size", 1.0),
                        )
                    else:
                        macd_hist_mean = None
                        macd_ma_key = task_cfg.get("macd_ma_key")
                        if macd_ma_key and "MACD_HIST" in df.columns:
                            window = 20
                            macd_hist_mean = df["MACD_HIST"].iloc[-window:].mean() if len(df) >= window else df["MACD_HIST"].mean()
                        signal = grid_trade.get_grid_signal(
                            latest,
                            grid_count=task_cfg.get("grid_count", 10),
                            grid_spread=task_cfg.get("grid_spread", 0.10),
                            ma_key=task_cfg.get("base_ma_key", "MA20"),
                            macd_ma_key=macd_ma_key,
                            macd_hist_mean=macd_hist_mean,
                        )
                signal_str = signal.get("signal", "观望")
                logger.debug(f"[OffHours] {user_id}/{symbol} 非交易时间，信号={signal_str}")
            else:
                signal_str = "观望"
                logger.debug(f"[OffHours] {user_id}/{symbol} 数据不足，信号=观望")
        except Exception as e:
            signal_str = "观望"
            logger.debug(f"[OffHours] {user_id}/{symbol} 计算信号异常: {e}")
        AutoTradeTask.update_last_check(task_cfg["id"], signal_str)

    @classmethod
    def _is_trading_time(cls) -> bool:
        from backend.utils.timezone import get_china_now
        now = get_china_now()
        if now.weekday() >= 5:
            return False
        hour, minute = now.hour, now.minute
        if (hour == 9 and minute >= 30) or (9 < hour < 11) or (hour == 11 and minute <= 30):
            return True
        if (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
            return True
        return False

    @classmethod
    def _get_sim_position(cls, user_id: int, symbol: str, portfolio: dict = None) -> dict:
        if portfolio is None:
            portfolio = st.get_portfolio(user_id)
        sim_positions = {p["symbol"]: p for p in (portfolio.get("positions", []) if portfolio else [])}
        pos = sim_positions.get(symbol, {})
        return {
            "shares": int(pos.get("shares", 0)) or 0,
            "avg_cost": float(pos.get("avg_cost", 0)) or 0,
        }

    @classmethod
    def _calc_task_cash(cls, allocated_funds: float, cur_shares: int, cur_avg_cost: float) -> float:
        position_value = cur_shares * cur_avg_cost if cur_shares > 0 else 0
        return allocated_funds - position_value

    @classmethod
    async def _check_stop_loss_take_profit(cls, task_cfg, close, cur_shares, cur_avg_cost) -> Optional[str]:
        if cur_shares <= 0 or cur_avg_cost <= 0:
            return None
        stop_loss_pct = task_cfg.get("stop_loss_pct", -5.0)
        take_profit_pct = task_cfg.get("take_profit_pct", 10.0)
        total_pnl_pct = (close - cur_avg_cost) / cur_avg_cost * 100
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]

        if total_pnl_pct <= stop_loss_pct:
            logger.warning(f"[StopLoss] {user_id}/{symbol} 触发止损 ({total_pnl_pct:.1f}% ≤ {stop_loss_pct:.1f}%)")
            await cls._force_close_position(user_id, symbol, close, cur_shares, task_cfg,
                                            f"止损触发 ({total_pnl_pct:.1f}%)", "stop_loss")
            AutoTradeTask.record_trade(task_cfg["id"], "sell")
            return "stop_loss"

        if total_pnl_pct >= take_profit_pct:
            logger.info(f"[TakeProfit] {user_id}/{symbol} 触发止盈 ({total_pnl_pct:.1f}% ≥ {take_profit_pct:.1f}%)")
            await cls._force_close_position(user_id, symbol, close, cur_shares, task_cfg,
                                            f"止盈触发 ({total_pnl_pct:.1f}%)", "take_profit")
            AutoTradeTask.record_trade(task_cfg["id"], "sell")
            return "take_profit"

        return None

    @classmethod
    def _calc_trade_signal(cls, task_cfg, latest, df) -> dict:
        try:
            strategy = StrategyFactory.get(task_cfg.get("strategy", "grid"))
            return strategy.calc_signal(latest, df, task_cfg)
        except ValueError:
            if task_cfg.get("strategy") == "ma_trend":
                return grid_trade.get_ma_trend_signal(
                    latest,
                    fast_ma_key=task_cfg.get("base_ma_key", "MA5"),
                    slow_ma_key=task_cfg.get("trend_ma_key") or "MA20",
                    position_size=task_cfg.get("position_size", 1.0),
                )
            macd_hist_mean = None
            macd_ma_key = task_cfg.get("macd_ma_key")
            if macd_ma_key and "MACD_HIST" in df.columns:
                window = 20
                macd_hist_mean = df["MACD_HIST"].iloc[-window:].mean() if len(df) >= window else df["MACD_HIST"].mean()
            return grid_trade.get_grid_signal(
                latest,
                grid_count=task_cfg.get("grid_count", 10),
                grid_spread=task_cfg.get("grid_spread", 0.10),
                ma_key=task_cfg.get("base_ma_key", "MA20"),
                macd_ma_key=macd_ma_key,
                macd_hist_mean=macd_hist_mean,
            )

    @classmethod
    def _apply_trend_filter(cls, signal, trend_above, trend_ma_key, user_id, symbol) -> dict:
        if trend_above is not None and signal["signal"] in ("买入", "卖出"):
            if not trend_above and signal["signal"] == "买入":
                logger.info(f"[TrendFilter] {user_id}/{symbol} 价格低于{trend_ma_key}，过滤买入信号")
                signal["signal"] = "观望"
                signal["action_desc"] = f"价格低于{trend_ma_key}，逆势不买入"
            elif trend_above and signal["signal"] == "卖出":
                logger.info(f"[TrendFilter] {user_id}/{symbol} 价格高于{trend_ma_key}，过滤卖出信号")
                signal["signal"] = "观望"
                signal["action_desc"] = f"价格高于{trend_ma_key}，逆势不卖出"
        return signal

    @classmethod
    def _calc_position_delta(cls, task_cfg, signal, close, cur_shares, allocated_funds) -> Optional[dict]:
        position_ratio = signal.get("position_ratio", 0.5)
        position_size = task_cfg.get("position_size", 1.0)
        max_position_ratio = position_size
        effective_ratio = round(min(position_ratio, max_position_ratio), 4)
        target_market_value = allocated_funds * effective_ratio
        current_market_value = cur_shares * close
        value_diff = target_market_value - current_market_value
        current_position_ratio = current_market_value / allocated_funds if allocated_funds > 0 else 0

        POSITION_MATCH_TOLERANCE = 0.03
        if abs(current_position_ratio - effective_ratio) < POSITION_MATCH_TOLERANCE:
            logger.debug(f"[PositionMatch] {task_cfg['user_id']}/{task_cfg['symbol']} 当前仓位 {current_position_ratio:.2%} ≈ 建议 {effective_ratio:.2%}，无需调仓")
            return None

        min_step_value = max(allocated_funds * MIN_STEP_VALUE_PCT, 100 * close)
        if abs(value_diff) < min_step_value:
            logger.debug(f"[StepGuard] {task_cfg['user_id']}/{task_cfg['symbol']} 仓位偏差金额 {value_diff:.2f} < 最小阈值 {min_step_value:.2f}，跳过")
            return None

        return {
            "value_diff": value_diff,
            "effective_ratio": effective_ratio,
            "current_position_ratio": current_position_ratio,
        }

    @classmethod
    def _execute_order(cls, task_cfg, delta, close, cur_shares, allocated_funds, trade_name, settings) -> Optional[dict]:
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]
        value_diff = delta["value_diff"]
        commission_rate = settings.get("commission_rate", 0.0003)
        min_commission = settings.get("min_commission", 5.0)
        stamp_tax_rate = settings.get("stamp_tax_rate", 0.001)
        transfer_fee_rate = settings.get("transfer_fee_rate", 0.00002)

        sim_pos = cls._get_sim_position(user_id, symbol)
        cur_shares = sim_pos["shares"]
        cur_avg_cost = sim_pos["avg_cost"]
        task_cash = cls._calc_task_cash(allocated_funds, cur_shares, cur_avg_cost)

        if value_diff > 0:
            shares = int(round(value_diff / close / 100)) * 100
            if shares < 100:
                return None
            amount = close * shares
            commission_est = max(amount * commission_rate, min_commission)
            if task_cash < (amount + commission_est):
                logger.warning(f"[CashGuard] {user_id}/{symbol} 任务现金不足 task_cash={task_cash:.2f} < need={amount + commission_est:.2f}")
                return None
            result = st.execute_trade(user_id, "buy", symbol, trade_name, close, shares, trade_type="auto")
            action_str = "买入"
        else:
            sell_amount = abs(value_diff)
            shares = int(round(sell_amount / close / 100)) * 100
            if shares < 100 or cur_shares < 100:
                return None
            shares = min(shares, cur_shares)
            shares = (shares // 100) * 100
            if shares < 100:
                return None
            result = st.execute_trade(user_id, "sell", symbol, trade_name, close, shares, trade_type="auto")
            action_str = "卖出"

        if result.get("success"):
            new_sim_pos = cls._get_sim_position(user_id, symbol)
            new_task_cash = cls._calc_task_cash(allocated_funds, new_sim_pos["shares"], new_sim_pos["avg_cost"])
            AutoTradeTask.update_runtime(
                task_cfg["id"],
                task_cash=new_task_cash,
                task_pnl=0,
                position_shares=new_sim_pos["shares"],
                position_avg_cost=new_sim_pos["avg_cost"],
                task_name=trade_name,
            )
            AutoTradeTask.record_trade(task_cfg["id"], action_str)
            logger.info(f"[AutoTradeScheduler] {user_id}/{symbol} {action_str} {shares}股 @ {close:.4f}, 建议仓位={delta['effective_ratio']:.2%}, 当前仓位={delta['current_position_ratio']:.2%}, 偏差={value_diff:.2f}")
            return {"action": action_str, "shares": shares, "close": close}

        return None

    @classmethod
    async def _check_and_trade(cls, task_cfg: dict, data_cache: Dict[str, Any] = None) -> None:
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]

        if data_cache and symbol in data_cache:
            df = data_cache[symbol]
        else:
            df = gold_data.get_full_data(symbol, datalen=90)
        if df is None or len(df) < 20:
            return

        latest = df.iloc[-1]
        close = float(latest["收盘"])
        allocated_funds = task_cfg.get("allocated_funds", 0)

        portfolio = st.get_portfolio(user_id)
        account_cash = float(portfolio["account"].get("cash", 0)) if portfolio and portfolio.get("account") else 0
        if account_cash <= 0:
            task_cash = task_cfg.get("task_cash", allocated_funds)
            if task_cash > 0:
                logger.warning(f"[Sync] {user_id}/{symbol} 模拟账户已无现金，暂停任务")
                AutoTradeTask.update_enabled(task_cfg["id"], False)
                return

        sim_pos = cls._get_sim_position(user_id, symbol, portfolio)
        cur_shares = sim_pos["shares"]
        cur_avg_cost = sim_pos["avg_cost"]
        task_cash = cls._calc_task_cash(allocated_funds, cur_shares, cur_avg_cost)

        sl_result = await cls._check_stop_loss_take_profit(task_cfg, close, cur_shares, cur_avg_cost)
        if sl_result:
            return

        trend_ma_key = task_cfg.get("trend_ma_key")
        trend_above = None
        if trend_ma_key:
            trend_ma = float(latest.get(trend_ma_key, 0))
            if trend_ma > 0:
                trend_above = close > trend_ma

        signal = cls._calc_trade_signal(task_cfg, latest, df)
        signal = cls._apply_trend_filter(signal, trend_above, trend_ma_key, user_id, symbol)

        signal_confirmed = AutoTradeTask.update_consecutive_signals(
            task_cfg["id"], signal["signal"], CONSECUTIVE_SIGNALS_REQUIRED
        )

        unrealized = (close - cur_avg_cost) * cur_shares if cur_shares > 0 else 0
        AutoTradeTask.update_runtime(
            task_cfg["id"],
            task_cash=task_cash,
            task_pnl=0,
            position_shares=cur_shares,
            position_avg_cost=cur_avg_cost,
            unrealized_pnl=unrealized,
            task_name=task_cfg.get("task_name", symbol),
        )

        if signal["signal"] not in ("买入", "卖出"):
            return
        if not signal_confirmed:
            return
        if AutoTradeTask.is_in_cooldown(task_cfg["id"]):
            return
        if not AutoTradeTask.can_trade_today(task_cfg["id"]):
            return

        delta = cls._calc_position_delta(task_cfg, signal, close, cur_shares, allocated_funds)
        if delta is None:
            return

        trade_name = latest.get("名称", symbol) or symbol
        settings = SimSettings.get(symbol)
        cls._execute_order(task_cfg, delta, close, cur_shares, allocated_funds, trade_name, settings)

    @classmethod
    async def _force_close_position(cls, user_id, symbol, close, shares, task_cfg, reason, close_type):
        if shares < 100:
            return

        shares = (shares // 100) * 100
        if shares < 100:
            return

        trade_name = task_cfg.get("task_name", symbol)
        result = st.execute_trade(user_id, "sell", symbol, trade_name, close, shares, trade_type="auto")

        if result.get("success"):
            allocated_funds = task_cfg.get("allocated_funds", 0)
            new_sim_pos = cls._get_sim_position(user_id, symbol)
            new_task_cash = cls._calc_task_cash(allocated_funds, new_sim_pos["shares"], new_sim_pos["avg_cost"])

            AutoTradeTask.update_runtime(
                task_cfg["id"],
                task_cash=new_task_cash,
                task_pnl=0,
                position_shares=new_sim_pos["shares"],
                position_avg_cost=new_sim_pos["avg_cost"],
                task_name=task_cfg.get("task_name", symbol),
            )
            logger.warning(f"[{close_type.upper()}] {user_id}/{symbol} 已清仓 {shares}股 @ {close:.4f}, 原因={reason}")
        else:
            logger.error(f"[{close_type.upper()}] {user_id}/{symbol} 清仓失败: {result.get('error', '')}")

    @classmethod
    def get_status(cls, user_id: int, symbol: str = None):
        """获取任务运行状态（供 API 查询用）"""
        scheduler_running = cls.is_running()
        logger.info(f"[Scheduler] get_status called: user_id={user_id}, symbol={symbol}, scheduler_running={scheduler_running}")
        
        def _calc_unrealized(task_cfg: dict) -> float:
            shares = task_cfg.get("position_shares", 0) or 0
            avg_cost = task_cfg.get("position_avg_cost", 0) or 0
            if shares <= 0 or avg_cost <= 0:
                return task_cfg.get("unrealized_pnl", 0) or 0
            try:
                df = cls._data_cache.get(task_cfg["symbol"]) if cls._data_cache else None
                if df is None or len(df) == 0:
                    df = gold_data.get_full_data(task_cfg["symbol"], datalen=5)
                if df is not None and len(df) > 0:
                    close = float(df["收盘"].iloc[-1])
                    return (close - avg_cost) * shares
            except Exception as e:
                logger.warning(f"[Scheduler] 计算实时浮动盈亏失败: {e}")
            return task_cfg.get("unrealized_pnl", 0) or 0

        if symbol:
            task_cfg = AutoTradeTask.find_by_symbol(user_id, symbol)
            if not task_cfg:
                return None
            task_enabled = task_cfg.get("enabled", False)
            running = scheduler_running and task_enabled
            logger.info(f"[Scheduler] task status: symbol={symbol}, enabled={task_enabled}, running={running}")
            signal = cls._calc_task_signal(task_cfg)
            return {
                "id": task_cfg["id"],
                "symbol": task_cfg["symbol"],
                "running": running,
                "task": task_cfg,
                "signal": signal,
                "task_cash": task_cfg.get("task_cash", task_cfg.get("allocated_funds", 0)),
                "task_pnl": task_cfg.get("task_pnl", 0),
                "task_position": {
                    "shares": task_cfg.get("position_shares", 0),
                    "avg_cost": task_cfg.get("position_avg_cost", 0),
                },
                "task_name": task_cfg.get("task_name", symbol),
                "unrealized_pnl": _calc_unrealized(task_cfg),
                "trade_count_today": task_cfg.get("trade_count_today", 0),
                "last_trade_time": task_cfg.get("last_trade_time"),
                "last_trade_direction": task_cfg.get("last_trade_direction"),
                "consecutive_signals": task_cfg.get("consecutive_signals", 0),
                "in_cooldown": AutoTradeTask.is_in_cooldown(task_cfg["id"]),
            }

        tasks = AutoTradeTask.find_by_user(user_id)
        result = []
        for t in tasks:
            task_enabled = t.get("enabled", False)
            running = scheduler_running and task_enabled
            logger.info(f"[Scheduler] task status: symbol={t['symbol']}, enabled={task_enabled}, running={running}")
            signal = cls._calc_task_signal(t)
            result.append({
                "id": t["id"],
                "symbol": t["symbol"],
                "running": running,
                "task": t,
                "signal": signal,
                "task_cash": t.get("task_cash", t.get("allocated_funds", 0)),
                "task_pnl": t.get("task_pnl", 0),
                "task_position": {
                    "shares": t.get("position_shares", 0),
                    "avg_cost": t.get("position_avg_cost", 0),
                },
                "task_name": t.get("task_name", t.get("symbol", "")),
                "unrealized_pnl": _calc_unrealized(t),
                "trade_count_today": t.get("trade_count_today", 0),
                "last_trade_time": t.get("last_trade_time"),
                "last_trade_direction": t.get("last_trade_direction"),
                "consecutive_signals": t.get("consecutive_signals", 0),
                "in_cooldown": AutoTradeTask.is_in_cooldown(t["id"]),
            })
        return result

    @classmethod
    def _calc_task_signal(cls, task_cfg: dict) -> Optional[Dict[str, Any]]:
        try:
            symbol = task_cfg.get("symbol")
            if not symbol:
                return None

            df = cls._data_cache.get(symbol) if cls._data_cache else None
            if df is None or len(df) < 20:
                df = gold_data.get_full_data(symbol, datalen=90)
            if df is None or len(df) < 20:
                return None

            latest = df.iloc[-1]
            close = float(latest["收盘"])

            strategy = task_cfg.get("strategy", "grid")

            try:
                strategy_obj = StrategyFactory.get(strategy)
                signal = strategy_obj.calc_signal(latest, df, task_cfg)
            except ValueError:
                if strategy == "ma_trend":
                    signal = grid_trade.get_ma_trend_signal(
                        latest,
                        fast_ma_key=task_cfg.get("base_ma_key", "MA5"),
                        slow_ma_key=task_cfg.get("trend_ma_key") or "MA20",
                        position_size=task_cfg.get("position_size", 1.0),
                    )
                else:
                    macd_hist_mean = None
                    macd_ma_key = task_cfg.get("macd_ma_key")
                    if macd_ma_key and "MACD_HIST" in df.columns:
                        window = 20
                        macd_hist_mean = df["MACD_HIST"].iloc[-window:].mean() if len(df) >= window else df["MACD_HIST"].mean()
                    signal = grid_trade.get_grid_signal(
                        latest,
                        grid_count=task_cfg.get("grid_count", 10),
                        grid_spread=task_cfg.get("grid_spread", 0.10),
                        ma_key=task_cfg.get("base_ma_key", "MA20"),
                        macd_ma_key=macd_ma_key,
                        macd_hist_mean=macd_hist_mean,
                    )

            signal["close"] = close
            return signal
        except Exception as e:
            logger.warning(f"计算任务信号失败: {e}")
            return None
