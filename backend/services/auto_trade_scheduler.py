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
from backend.routes.realtime import get_realtime
from backend.utils.timezone import china_now_naive
from backend.utils.symbol import normalize_symbol

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL = 30
CONSECUTIVE_SIGNALS_REQUIRED = 2   # 交易信号需连续 N 次相同才执行
MIN_STEP_VALUE_PCT = 0.02          # 最小调仓阈值：分配资金的 2%

# A股交易规则常量
MIN_TRADE_UNITS = 100              # 最小交易单位（股）
POSITION_MATCH_TOLERANCE = 0.03    # 仓位匹配容差（3%）
MAX_PRICE_DEVIATION_PCT = 5.0      # 最大价格偏离百分比
CACHE_TTL = 60                     # 数据缓存有效期（秒）

STRATEGY_TYPE_MAP = {
    "grid": "网格策略",
    "ma_trend": "均线趋势",
    "manual": "手动交易",
}

def _build_trade_type(strategy: str, close_type: str = None) -> str:
    if close_type:
        return f"auto_{close_type}"
    if strategy and strategy != "manual":
        return f"auto_{strategy}"
    return "manual"


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
    def _batch_update_all_positions(cls, all_tasks: list):
        user_ids = list(set(t.get("user_id") for t in all_tasks if t.get("user_id")))
        for uid in user_ids:
            try:
                positions = st.get_portfolio(uid)
                if not positions or not positions.get("positions"):
                    continue
                pos_symbols = list(set(p["symbol"] for p in positions["positions"] if p.get("shares", 0) > 0))
                if not pos_symbols:
                    continue
                sym_str = ",".join(pos_symbols)
                rt_result = get_realtime(sym_str)
                realtime_map = {}
                if rt_result.get("code") == 0 and rt_result.get("data"):
                    for sym, item in rt_result["data"].items():
                        if item and item.get("price"):
                            realtime_map[sym] = item
                            alt = sym.replace("sh", "").replace("sz", "").replace("bj", "")
                            if alt != sym:
                                realtime_map[alt] = item
                if realtime_map:
                    st.update_prices(uid, realtime_map)
                    logger.info(f"[BatchPrice] user_id={uid} 批量更新 {len(realtime_map)} 个持仓价格")
            except Exception as e:
                logger.warning(f"[BatchPrice] user_id={uid} 批量更新持仓价格失败: {e}")

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

        cls._batch_update_all_positions(all_tasks)

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
        """
        判断当前是否为交易时间
        
        Returns:
            bool: True 为交易时间，False 为非交易时间
        """
        from backend.utils.timezone import get_china_now
        from backend.services.gold_data import is_trade_date
        now = get_china_now()

        # 首先检查是否为交易日
        # if not is_trade_date(now.date()):
        #     return False

        # 转换为分钟数便于比较（小时*60 + 分钟）
        hour_minute = now.hour * 60 + now.minute
        
        # 上午 9:30-11:30 (570-690分钟)
        morning = 9 * 60 + 30 <= hour_minute <= 11 * 60 + 30
        # 下午 13:00-15:00 (780-900分钟)
        afternoon = 13 * 60 <= hour_minute <= 15 * 60
        return  True
        # return morning or afternoon

    @classmethod
    def _get_sim_position(cls, user_id: int, symbol: str, strategy: str = None, portfolio: dict = None) -> dict:
        """
        从模拟账户读取指定策略的持仓数据
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            strategy: 策略类型，用于隔离不同策略的持仓
            portfolio: 可选的账户信息缓存
            
        Returns:
            dict: 包含 shares 和 avg_cost 的持仓信息
        """
        from backend.models.simulation import SimulationPosition
        if strategy:
            pos = SimulationPosition.find_by_strategy(user_id, symbol, strategy)
            if pos:
                return {
                    "shares": int(pos.get("shares", 0)) or 0,
                    "avg_cost": float(pos.get("avg_cost", 0)) or 0,
                }
            return {"shares": 0, "avg_cost": 0}
        if portfolio is None:
            portfolio = st.get_portfolio(user_id)
        sim_positions = {p["symbol"]: p for p in (portfolio.get("positions", []) if portfolio else [])}
        pos = sim_positions.get(symbol, {})
        return {
            "shares": int(pos.get("shares", 0)) or 0,
            "avg_cost": float(pos.get("avg_cost", 0)) or 0,
        }

    @classmethod
    def _get_task_position(cls, task_cfg: dict) -> dict:
        """
        优先从模拟账户读取该策略的持仓数据，fallback到任务自身配置
        
        按策略类型隔离持仓，确保不同策略的持仓互不干扰。
        
        Args:
            task_cfg: 任务配置字典，包含 user_id, symbol, strategy 等字段
            
        Returns:
            dict: 包含 shares 和 avg_cost 的持仓信息
        """
        from backend.models.simulation import SimulationPosition
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]
        strategy = task_cfg.get("strategy", "grid")

        pos = SimulationPosition.find_by_strategy(user_id, symbol, strategy)
        if pos and pos.get("shares", 0) > 0:
            return {
                "shares": int(pos.get("shares", 0)),
                "avg_cost": float(pos.get("avg_cost", 0)),
            }

        return {
            "shares": int(task_cfg.get("position_shares", 0) or 0),
            "avg_cost": float(task_cfg.get("position_avg_cost", 0) or 0),
        }

    @classmethod
    def _calc_task_cash(cls, allocated_funds: float, cur_shares: int, cur_avg_cost: float) -> float:
        position_value = cur_shares * cur_avg_cost if cur_shares > 0 else 0
        return allocated_funds - position_value

    @classmethod
    async def _check_stop_loss_take_profit(cls, task_cfg, close, cur_shares, cur_avg_cost, trade_price=None) -> Optional[str]:
        if cur_shares <= 0 or cur_avg_cost <= 0:
            return None
        if trade_price is None:
            trade_price = close
        stop_loss_pct = task_cfg.get("stop_loss_pct", -5.0)
        take_profit_pct = task_cfg.get("take_profit_pct", 10.0)
        total_pnl_pct = (close - cur_avg_cost) / cur_avg_cost * 100
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]

        if total_pnl_pct <= stop_loss_pct:
            logger.warning(f"[StopLoss] {user_id}/{symbol} 触发止损 ({total_pnl_pct:.1f}% ≤ {stop_loss_pct:.1f}%)")
            await cls._force_close_position(user_id, symbol, trade_price, cur_shares, task_cfg,
                                            f"止损触发 ({total_pnl_pct:.1f}%)", "stop_loss")
            AutoTradeTask.record_trade(task_cfg["id"], "sell")
            return "stop_loss"

        if total_pnl_pct >= take_profit_pct:
            logger.info(f"[TakeProfit] {user_id}/{symbol} 触发止盈 ({total_pnl_pct:.1f}% ≥ {take_profit_pct:.1f}%)")
            await cls._force_close_position(user_id, symbol, trade_price, cur_shares, task_cfg,
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

        sim_pos = cls._get_task_position(task_cfg)
        cur_shares = sim_pos["shares"]
        cur_avg_cost = sim_pos["avg_cost"]
        task_cash = cls._calc_task_cash(allocated_funds, cur_shares, cur_avg_cost)

        current_market_value = cur_shares * close
        current_position_ratio = current_market_value / allocated_funds if allocated_funds > 0 else 0
        if abs(current_position_ratio - delta["effective_ratio"]) < POSITION_MATCH_TOLERANCE:
            logger.debug(f"[ExecuteGuard] {user_id}/{symbol} 执行前仓位已匹配 {current_position_ratio:.2%} ≈ {delta['effective_ratio']:.2%}，跳过")
            return None

        strategy = task_cfg.get("strategy", "grid")
        specific_trade_type = _build_trade_type(strategy)
        strategy_type = strategy if strategy != "manual" else "manual"

        if value_diff > 0:
            if close <= 0:
                logger.warning(f"[CashGuard] {user_id}/{symbol} 价格无效 close={close}")
                return None
            shares = int(round(value_diff / close / MIN_TRADE_UNITS)) * MIN_TRADE_UNITS
            if shares < MIN_TRADE_UNITS:
                return None
            amount = close * shares
            commission_est = max(amount * commission_rate, min_commission)
            if task_cash < (amount + commission_est):
                max_affordable_amount = task_cash - max(task_cash * commission_rate, min_commission)
                if max_affordable_amount <= 0:
                    logger.warning(
                        f"[CashGuard] {user_id}/{symbol} 任务现金不足以支付最低佣金 task_cash={task_cash:.2f}")
                    return None
                max_shares = int(max_affordable_amount / close / MIN_TRADE_UNITS) * MIN_TRADE_UNITS
                if max_shares < MIN_TRADE_UNITS:
                    logger.warning(
                        f"[CashGuard] {user_id}/{symbol} 任务现金不足 task_cash={task_cash:.2f} < need={amount + commission_est:.2f}")
                    return None
                logger.info(
                    f"[CashGuard] {user_id}/{symbol} 资金不足调整: 原计划{shares}股 → 调整为{max_shares}股 (task_cash={task_cash:.2f})")
                shares = max_shares
                amount = close * shares
                commission_est = max(amount * commission_rate, min_commission)
            result = st.execute_trade(user_id, "buy", symbol, trade_name, close, shares, trade_type=specific_trade_type,
                                      strategy_type=strategy_type)
            action_str = "买入"
        else:
            sell_amount = abs(value_diff)
            shares = int(round(sell_amount / close / MIN_TRADE_UNITS)) * MIN_TRADE_UNITS
            if shares < MIN_TRADE_UNITS or cur_shares < MIN_TRADE_UNITS:
                return None
            shares = min(shares, cur_shares)
            shares = (shares // MIN_TRADE_UNITS) * MIN_TRADE_UNITS
            if shares < MIN_TRADE_UNITS:
                return None
            result = st.execute_trade(user_id, "sell", symbol, trade_name, close, shares, trade_type=specific_trade_type, strategy_type=strategy_type)
            action_str = "卖出"

        if result.get("success"):
            from backend.models.simulation import SimulationPosition
            old_shares = cur_shares
            old_avg_cost = cur_avg_cost

            if action_str == "买入":
                new_shares = old_shares + shares
                if new_shares > 0:
                    new_avg_cost = (old_shares * old_avg_cost + shares * close) / new_shares
                else:
                    new_avg_cost = close
            else:
                new_shares = max(0, old_shares - shares)
                new_avg_cost = old_avg_cost

            sim_pos = SimulationPosition.find_by_strategy(user_id, symbol, strategy_type)
            sim_shares = int(sim_pos.get("shares", 0)) if sim_pos else 0
            sim_avg_cost = float(sim_pos.get("avg_cost", 0)) if sim_pos else 0

            # 以任务计算值为准，强制同步到数据库
            if sim_shares > 0 and abs(sim_avg_cost - new_avg_cost) > 0.001:
                logger.warning(
                    f"[CostSync] {user_id}/{symbol}[{strategy_type}] 持仓成本不一致: "
                    f"任务计算={new_avg_cost:.4f} (基于{old_shares}股@{old_avg_cost:.4f}+{shares}股@{close:.4f}), "
                    f"模拟账户={sim_avg_cost:.4f} ({sim_shares}股), "
                    f"差异={abs(sim_avg_cost - new_avg_cost):.4f}, 强制修正"
                )
                # 强制更新数据库中的持仓成本
                SimulationPosition.upsert(
                    user_id, symbol, trade_name,
                    new_shares, new_avg_cost,
                    close, strategy_type
                )

            if sim_shares != new_shares:
                logger.info(
                    f"[CostSync] {user_id}/{symbol}[{strategy_type}] 持仓数量差异: 任务计算={new_shares}, 模拟账户={sim_shares}, 以任务计算值为准"
                )

            new_task_cash = cls._calc_task_cash(allocated_funds, new_shares, new_avg_cost)
            AutoTradeTask.update_runtime(
                task_cfg["id"],
                task_cash=new_task_cash,
                task_pnl=0,
                position_shares=new_shares,
                position_avg_cost=new_avg_cost,
                task_name=trade_name,
            )
            AutoTradeTask.record_trade(task_cfg["id"], action_str)

            is_loss = False
            if action_str == "卖出" and cur_shares > 0 and cur_avg_cost > 0:
                is_loss = close < cur_avg_cost
            elif action_str == "买入":
                is_loss = False
            AutoTradeTask.update_consecutive_losses(task_cfg["id"], is_loss)

            logger.info(f"[AutoTradeScheduler] {user_id}/{symbol} {action_str} {shares}股 @ {close:.4f}, 建议仓位={delta['effective_ratio']:.2%}, 当前仓位={delta['current_position_ratio']:.2%}, 偏差={value_diff:.2f}")
            
            # 发送邮件通知
            try:
                from backend.utils.notification import send_trade_email
                import os
                
                logger.info(f"[Email] 准备发送交易通知: user_id={user_id}, symbol={symbol}, action={action_str}")
                
                notify_emails = os.getenv('EMAIL_NOTIFY_RECEIVERS', '')
                logger.debug(f"[Email] EMAIL_NOTIFY_RECEIVERS 配置: {notify_emails if notify_emails else '(未设置)'}")
                
                if notify_emails:
                    email_list = [email.strip() for email in notify_emails.split(',') if email.strip()]
                    logger.info(f"[Email] 解析收件人列表: {email_list}")
                    
                    if email_list:
                        logger.info(f"[Email] 开始发送邮件通知...")
                        result = send_trade_email(
                            to_emails=email_list,
                            user_id=user_id,
                            symbol=symbol,
                            action=action_str,
                            shares=shares,
                            price=close,
                            strategy=strategy,
                            task_name=trade_name
                        )
                        
                        if result:
                            logger.info(f"[Email] ✅ 交易通知邮件发送成功: {action_str} {symbol}")
                        else:
                            logger.warning(f"[Email] ⚠️ 交易通知邮件发送失败（返回 False）: {action_str} {symbol}")
                    else:
                        logger.warning(f"[Email] ⚠️ 收件人列表为空，跳过邮件发送")
                else:
                    logger.info(f"[Email] ℹ️ 未配置 EMAIL_NOTIFY_RECEIVERS，跳过邮件发送")
                    
            except Exception as e:
                logger.error(f"[Email] ❌ 发送交易通知邮件异常: {type(e).__name__}: {e}", exc_info=True)
            
            return {"action": action_str, "shares": shares, "close": close}

        return None

    @classmethod
    async def _check_and_trade(cls, task_cfg: dict, data_cache: Dict[str, Any] = None) -> None:
        user_id = task_cfg["user_id"]
        symbol = task_cfg["symbol"]

        # 检查数据缓存是否过期
        import time as _time
        if cls._data_cache_ts and (_time.time() - cls._data_cache_ts) > CACHE_TTL:
            logger.warning(f"[Cache] {user_id}/{symbol} 数据已过期 ({_time.time() - cls._data_cache_ts:.0f}s)，重新获取")
            cls._data_cache = {}
            cls._data_cache_ts = 0

        if data_cache and symbol in data_cache:
            df = data_cache[symbol]
        else:
            df = gold_data.get_full_data(symbol, datalen=90)
        if df is None or len(df) < 20:
            return

        latest = df.iloc[-1]
        kline_close = float(latest["收盘"])
        allocated_funds = task_cfg.get("allocated_funds", 0)

        realtime_price = None
        try:
            rt = get_realtime(symbol)
            logger.debug(f"[Realtime] {user_id}/{symbol} 实时行情响应: code={rt.get('code')}, has_data={bool(rt.get('data'))}")
            if rt.get("code") == 0 and rt.get("data"):
                data = rt["data"]
                symbol_data = data.get(symbol) or data.get(normalize_symbol(symbol)) or {}
                if symbol_data and symbol_data.get("price") and float(symbol_data["price"]) > 0:
                    realtime_price = float(symbol_data["price"])
                    logger.info(f"[Realtime] {user_id}/{symbol} 获取实时价格成功: {realtime_price:.4f}")
        except Exception as e:
            logger.error(f"[Realtime] {user_id}/{symbol} 获取实时价格异常: {e}")

        if realtime_price and realtime_price > 0:
            close = realtime_price
        else:
            logger.warning(f"[Realtime] {user_id}/{symbol} 实时价格不可用，使用K线收盘价 {kline_close:.4f} 更新持仓（不交易）")
            st.update_position_price(user_id, symbol, kline_close)
            AutoTradeTask.update_last_check(task_cfg["id"], "观望")
            return

        st.update_position_price(user_id, symbol, close)
        logger.debug(f"[PriceUpdate] {user_id}/{symbol} 巡检更新持仓价格: {close:.4f}")

        portfolio = st.get_portfolio(user_id)
        account_cash = float(portfolio["account"].get("cash", 0)) if portfolio and portfolio.get("account") else 0
        if account_cash <= 0:
            task_cash = task_cfg.get("task_cash", allocated_funds)
            if task_cash > 0:
                logger.warning(f"[Sync] {user_id}/{symbol} 模拟账户已无现金，暂停任务")
                AutoTradeTask.update_enabled(task_cfg["id"], False)
                return

        sim_pos = cls._get_task_position(task_cfg)
        cur_shares = sim_pos["shares"]
        cur_avg_cost = sim_pos["avg_cost"]
        task_cash = cls._calc_task_cash(allocated_funds, cur_shares, cur_avg_cost)

        current_value = task_cash + cur_shares * close
        if allocated_funds > 0 and current_value <= 0:
            logger.warning(f"[Drawdown] {user_id}/{symbol} 任务净值归零，暂停任务")
            AutoTradeTask.update_enabled(task_cfg["id"], False)
            return

        if allocated_funds > 0:
            drawdown_pct = AutoTradeTask.update_peak_and_drawdown(task_cfg["id"], current_value)
            max_drawdown_pct = task_cfg.get("max_drawdown_pct", -15.0)
            if max_drawdown_pct < 0 and drawdown_pct <= max_drawdown_pct:
                logger.warning(f"[Drawdown] {user_id}/{symbol} 触发最大回撤保护 (回撤{drawdown_pct:.1f}% ≤ 阈值{max_drawdown_pct:.1f}%)，暂停任务")
                AutoTradeTask.update_enabled(task_cfg["id"], False)
                return

        sl_result = await cls._check_stop_loss_take_profit(task_cfg, close, cur_shares, cur_avg_cost, close)
        if sl_result:
            return

        trend_ma_key = task_cfg.get("trend_ma_key")
        trend_above = None
        if trend_ma_key:
            trend_ma = float(latest.get(trend_ma_key, 0))
            if trend_ma > 0:
                trend_above = close > trend_ma

        effective_strategy = task_cfg.get("strategy", "grid")
        if task_cfg.get("adaptive_strategy", False):
            from backend.services.strategies.multi_factor import calc_composite_score, get_recommended_strategy
            composite = calc_composite_score(latest, df)
            recommended = get_recommended_strategy(composite["score"])
            if recommended != effective_strategy:
                logger.info(f"[AdaptiveStrategy] {user_id}/{symbol} 策略自适应切换: {effective_strategy} → {recommended} (评分={composite['score']:.1f}, 状态={composite['market_state_cn']})")
                effective_strategy = recommended
            task_cfg = {**task_cfg, "strategy": effective_strategy}

        latest_with_realtime = latest.copy()
        latest_with_realtime['收盘'] = close
        signal = cls._calc_trade_signal(task_cfg, latest_with_realtime, df)
        signal = cls._apply_trend_filter(signal, trend_above, trend_ma_key, user_id, symbol)

        if task_cfg.get("use_multi_factor", False):
            from backend.services.strategies.multi_factor import calc_composite_score
            composite = calc_composite_score(latest, df)
            mf_score = composite["score"]
            mf_signal = composite["signal"]
            mf_position = composite["position_suggestion"]
            logger.info(f"[MultiFactor] {user_id}/{symbol} 综合评分={mf_score:.1f}, 市场状态={composite['market_state_cn']}, 评分信号={mf_signal}, 建议仓位={mf_position:.0%}")

            if signal["signal"] in ("买入", "卖出") and mf_signal != signal["signal"] and mf_score * (-1 if signal["signal"] == "买入" else 1) > 30:
                logger.info(f"[MultiFactor] {user_id}/{symbol} 多因子信号与策略信号矛盾(策略={signal['signal']}, 评分={mf_signal}), 过滤策略信号")
                signal["signal"] = "观望"
                signal["action_desc"] = f"多因子评分{mf_score:.0f}与策略矛盾，暂不操作"

            if signal["signal"] in ("买入", "卖出"):
                original_ratio = signal.get("position_ratio", 0.5)
                adjusted_ratio = original_ratio * mf_position
                signal["position_ratio"] = round(max(0.1, min(1.0, adjusted_ratio)), 4)
                signal["action_desc"] = f"{signal.get('action_desc', '')} [评分{mf_score:.0f}仓位{mf_position:.0%}]"

        signal_confirmed = AutoTradeTask.update_consecutive_signals(
            task_cfg["id"], signal["signal"], CONSECUTIVE_SIGNALS_REQUIRED
        )

        unrealized = (close - cur_avg_cost) * cur_shares if cur_shares > 0 else 0
        AutoTradeTask.update_runtime(
            task_cfg["id"],
            task_cash=task_cash,
            task_pnl=0,
            position_shares=int(task_cfg.get("position_shares", 0) or 0),
            position_avg_cost=float(task_cfg.get("position_avg_cost", 0) or 0),
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
        if shares < MIN_TRADE_UNITS:
            return

        shares = (shares // MIN_TRADE_UNITS) * MIN_TRADE_UNITS
        if shares < MIN_TRADE_UNITS:
            return

        trade_name = task_cfg.get("task_name", symbol)
        strategy = task_cfg.get("strategy", "grid")
        specific_trade_type = _build_trade_type(strategy, close_type)
        strategy_type = strategy if strategy != "manual" else "manual"
        result = st.execute_trade(user_id, "sell", symbol, trade_name, close, shares, trade_type=specific_trade_type, strategy_type=strategy_type)

        if result.get("success"):
            allocated_funds = task_cfg.get("allocated_funds", 0)
            new_task_cash = cls._calc_task_cash(allocated_funds, 0, 0)

            AutoTradeTask.update_runtime(
                task_cfg["id"],
                task_cash=new_task_cash,
                task_pnl=0,
                position_shares=0,
                position_avg_cost=0,
                task_name=task_cfg.get("task_name", symbol),
            )
            is_loss = close < (task_cfg.get("position_avg_cost", 0) or 0)
            AutoTradeTask.update_consecutive_losses(task_cfg["id"], is_loss)
            logger.warning(f"[{close_type.upper()}] {user_id}/{symbol} 已清仓 {shares}股 @ {close:.4f}, 原因={reason}")
            
            # 发送止损/止盈邮件通知
            try:
                from backend.utils.notification import send_trade_email
                import os
                
                logger.info(f"[Email] 准备发送{close_type}通知: user_id={user_id}, symbol={symbol}, reason={reason}")
                
                notify_emails = os.getenv('EMAIL_NOTIFY_RECEIVERS', '')
                logger.debug(f"[Email] EMAIL_NOTIFY_RECEIVERS 配置: {notify_emails if notify_emails else '(未设置)'}")
                
                if notify_emails:
                    email_list = [email.strip() for email in notify_emails.split(',') if email.strip()]
                    logger.info(f"[Email] 解析收件人列表: {email_list}")
                    
                    if email_list:
                        strategy = task_cfg.get("strategy", "grid")
                        trade_name = task_cfg.get("task_name", symbol)
                        
                        logger.info(f"[Email] 开始发送{close_type}通知邮件...")
                        result = send_trade_email(
                            to_emails=email_list,
                            user_id=user_id,
                            symbol=symbol,
                            action="卖出",
                            shares=shares,
                            price=close,
                            strategy=strategy,
                            task_name=trade_name,
                            reason=reason
                        )
                        
                        if result:
                            logger.info(f"[Email] ✅ {close_type}通知邮件发送成功: {symbol}")
                        else:
                            logger.warning(f"[Email] ⚠️ {close_type}通知邮件发送失败（返回 False）: {symbol}")
                    else:
                        logger.warning(f"[Email] ⚠️ 收件人列表为空，跳过邮件发送")
                else:
                    logger.info(f"[Email] ℹ️ 未配置 EMAIL_NOTIFY_RECEIVERS，跳过邮件发送")
                    
            except Exception as e:
                logger.error(f"[Email] ❌ 发送{close_type}通知邮件异常: {type(e).__name__}: {e}", exc_info=True)
        else:
            logger.error(f"[{close_type.upper()}] {user_id}/{symbol} 清仓失败: {result.get('error', '')}")

    @classmethod
    def get_status(cls, user_id: int, symbol: str = None):
        """获取任务运行状态（供 API 查询用）"""
        scheduler_running = cls.is_running()
        logger.info(f"[Scheduler] get_status called: user_id={user_id}, symbol={symbol}, scheduler_running={scheduler_running}")
        
        def _calc_unrealized(task_cfg: dict, rt_price: float = 0) -> float:
            shares = task_cfg.get("position_shares", 0) or 0
            avg_cost = task_cfg.get("position_avg_cost", 0) or 0
            if shares <= 0 or avg_cost <= 0:
                return 0
            close = rt_price
            if close <= 0:
                try:
                    df = cls._data_cache.get(task_cfg["symbol"]) if cls._data_cache else None
                    if df is None or len(df) == 0:
                        df = gold_data.get_full_data(task_cfg["symbol"], datalen=5)
                    if df is not None and len(df) > 0:
                        close = float(df["收盘"].iloc[-1])
                except Exception as e:
                    logger.warning(f"[Scheduler] 计算实时浮动盈亏失败: {e}")
            if close <= 0:
                return 0
            return (close - avg_cost) * shares

        def _get_realtime_info(symbol: str, rt_cache: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
            if symbol in rt_cache:
                return rt_cache[symbol]
            from backend.utils.symbol import strip_prefix
            alt = strip_prefix(symbol)
            if alt in rt_cache:
                return rt_cache[alt]
            return {"price": 0, "change_pct": 0, "name": ""}

        def _batch_fetch_realtime(symbols: list) -> Dict[str, Dict[str, Any]]:
            cache: Dict[str, Dict[str, Any]] = {}
            if not symbols:
                return cache
            try:
                from backend.routes.realtime import get_realtime
                from backend.utils.symbol import strip_prefix
                sym_str = ",".join(symbols)
                result = get_realtime(sym_str)
                if result.get("code") == 0 and result.get("data"):
                    data = result["data"]
                    for sym, item in data.items():
                        cache[sym] = {
                            "price": item.get("price", 0),
                            "change_pct": item.get("change_pct", 0),
                            "name": item.get("name", ""),
                        }
                        alt = strip_prefix(sym)
                        if alt != sym:
                            cache[alt] = cache[sym]
            except Exception as e:
                logger.warning(f"[Scheduler] 批量获取实时价格失败: {e}")
            return cache

        def _calc_composite(task_cfg: dict) -> Optional[Dict[str, Any]]:
            try:
                df = cls._data_cache.get(task_cfg["symbol"]) if cls._data_cache else None
                if df is None or len(df) < 20:
                    df = gold_data.get_full_data(task_cfg["symbol"], datalen=90)
                if df is None or len(df) < 20:
                    return None
                from backend.services.strategies.multi_factor import calc_composite_score
                return calc_composite_score(df.iloc[-1], df)
            except Exception:
                return None

        if symbol:
            task_cfg = AutoTradeTask.find_by_symbol(user_id, symbol)
            if not task_cfg:
                return None
            rt_cache = _batch_fetch_realtime([symbol])
            task_enabled = task_cfg.get("enabled", False)
            running = scheduler_running and task_enabled
            logger.info(f"[Scheduler] task status: symbol={symbol}, enabled={task_enabled}, running={running}")
            signal = cls._calc_task_signal(task_cfg)
            composite = _calc_composite(task_cfg)
            rt = _get_realtime_info(symbol, rt_cache)
            return {
                "id": task_cfg["id"],
                "symbol": task_cfg["symbol"],
                "running": running,
                "task": task_cfg,
                "signal": signal,
                "composite_score": composite,
                "task_cash": task_cfg.get("task_cash", task_cfg.get("allocated_funds", 0)),
                "task_pnl": task_cfg.get("task_pnl", 0),
                "task_position": {
                    "shares": task_cfg.get("position_shares", 0),
                    "avg_cost": task_cfg.get("position_avg_cost", 0),
                },
                "task_name": task_cfg.get("task_name", symbol),
                "unrealized_pnl": _calc_unrealized(task_cfg, rt["price"]),
                "realtime_price": rt["price"],
                "price_change_pct": rt["change_pct"],
                "stock_name": rt["name"],
                "trade_count_today": task_cfg.get("trade_count_today", 0),
                "last_trade_time": task_cfg.get("last_trade_time"),
                "last_trade_direction": task_cfg.get("last_trade_direction"),
                "consecutive_signals": task_cfg.get("consecutive_signals", 0),
                "in_cooldown": AutoTradeTask.is_in_cooldown(task_cfg["id"]),
            }

        tasks = AutoTradeTask.find_by_user(user_id)
        all_symbols = list({t["symbol"] for t in tasks})
        rt_cache = _batch_fetch_realtime(all_symbols)
        result = []
        for t in tasks:
            task_enabled = t.get("enabled", False)
            running = scheduler_running and task_enabled
            logger.info(f"[Scheduler] task status: symbol={t['symbol']}, enabled={task_enabled}, running={running}")
            signal = cls._calc_task_signal(t)
            composite = _calc_composite(t)
            rt = _get_realtime_info(t["symbol"], rt_cache)
            result.append({
                "id": t["id"],
                "symbol": t["symbol"],
                "running": running,
                "task": t,
                "signal": signal,
                "composite_score": composite,
                "task_cash": t.get("task_cash", t.get("allocated_funds", 0)),
                "task_pnl": t.get("task_pnl", 0),
                "task_position": {
                    "shares": t.get("position_shares", 0),
                    "avg_cost": t.get("position_avg_cost", 0),
                },
                "task_name": t.get("task_name", t.get("symbol", "")),
                "unrealized_pnl": _calc_unrealized(t, rt["price"]),
                "realtime_price": rt["price"],
                "price_change_pct": rt["change_pct"],
                "stock_name": rt["name"],
                "trade_count_today": t.get("trade_count_today", 0),
                "last_trade_time": t.get("last_trade_time"),
                "last_trade_direction": t.get("last_trade_direction"),
                "consecutive_signals": t.get("consecutive_signals", 0),
                "in_cooldown": AutoTradeTask.is_in_cooldown(t["id"]),
            })
        return result

    @classmethod
    def get_task_summary(cls, user_id: int) -> Dict[str, Any]:
        """
        计算所有自动交易任务的汇总数据，用于与共享账户对账。
        
        返回:
        - total_allocated_funds: 所有任务分配资金总和
        - total_task_cash: 所有任务剩余可用资金总和
        - total_position_value: 所有任务持仓市值总和
        - total_unrealized_pnl: 所有任务浮动盈亏总和
        - positions_by_symbol: 按股票聚合的持仓数据
        - account_comparison: 与共享账户的对比
        """
        tasks = AutoTradeTask.find_by_user(user_id)
        if not tasks:
            return {
                "total_allocated_funds": 0,
                "total_task_cash": 0,
                "total_position_value": 0,
                "total_unrealized_pnl": 0,
                "positions_by_symbol": {},
                "account_comparison": None,
            }

        all_symbols = list({t["symbol"] for t in tasks})
        rt_cache: Dict[str, Dict[str, Any]] = {}
        try:
            from backend.routes.realtime import get_realtime
            from backend.utils.symbol import strip_prefix
            sym_str = ",".join(all_symbols)
            result = get_realtime(sym_str)
            if result.get("code") == 0 and result.get("data"):
                data = result["data"]
                for sym, item in data.items():
                    rt_cache[sym] = {
                        "price": item.get("price", 0),
                        "change_pct": item.get("change_pct", 0),
                        "name": item.get("name", ""),
                    }
                    alt = strip_prefix(sym)
                    if alt != sym:
                        rt_cache[alt] = rt_cache[sym]
        except Exception as e:
            logger.warning(f"[Scheduler] get_task_summary 获取实时价格失败: {e}")

        total_allocated_funds = 0.0
        total_task_cash = 0.0
        total_position_value = 0.0
        total_unrealized_pnl = 0.0
        positions_by_symbol: Dict[str, Dict[str, Any]] = {}

        for t in tasks:
            allocated = float(t.get("allocated_funds", 0) or 0)
            shares = int(t.get("position_shares", 0) or 0)
            avg_cost = float(t.get("position_avg_cost", 0) or 0)
            task_cash = float(t.get("task_cash", allocated) or allocated)

            total_allocated_funds += allocated
            total_task_cash += task_cash

            symbol = t["symbol"]
            rt = rt_cache.get(symbol, {})
            price = float(rt.get("price", 0) or 0)
            if price <= 0:
                price = avg_cost

            position_value = shares * price
            unrealized = (price - avg_cost) * shares if shares > 0 and avg_cost > 0 else 0

            total_position_value += position_value
            total_unrealized_pnl += unrealized

            if symbol not in positions_by_symbol:
                positions_by_symbol[symbol] = {
                    "symbol": symbol,
                    "total_shares": 0,
                    "total_value": 0.0,
                    "tasks": [],
                }
            positions_by_symbol[symbol]["total_shares"] += shares
            positions_by_symbol[symbol]["total_value"] += position_value
            positions_by_symbol[symbol]["tasks"].append({
                "id": t["id"],
                "strategy": t.get("strategy", "grid"),
                "shares": shares,
                "avg_cost": avg_cost,
                "task_cash": task_cash,
                "unrealized_pnl": unrealized,
            })

        portfolio = st.get_portfolio(user_id)
        account_comparison = None
        if portfolio and portfolio.get("account"):
            account = portfolio["account"]
            account_comparison = {
                "account_cash": float(account.get("cash", 0) or 0),
                "account_market_value": float(account.get("market_value", 0) or 0),
                "account_unrealized_pnl": float(account.get("unrealized_pnl", 0) or 0),
                "account_realized_pnl": float(account.get("realized_pnl", 0) or 0),
                "task_total_cash": round(total_task_cash, 2),
                "task_total_position_value": round(total_position_value, 2),
                "task_total_unrealized_pnl": round(total_unrealized_pnl, 2),
                "cash_diff": round(float(account.get("cash", 0) or 0) - total_task_cash, 2),
                "position_diff": round(float(account.get("market_value", 0) or 0) - total_position_value, 2),
                "is_consistent": abs(float(account.get("cash", 0) or 0) - total_task_cash) < 1.0,
            }

        return {
            "total_allocated_funds": round(total_allocated_funds, 2),
            "total_task_cash": round(total_task_cash, 2),
            "total_position_value": round(total_position_value, 2),
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "positions_by_symbol": positions_by_symbol,
            "account_comparison": account_comparison,
            "task_count": len(tasks),
        }

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
