"""Auto Trade Service - Multi-task grid trading automation"""
import asyncio
from datetime import datetime
from typing import Dict, Any

from backend.models.auto_trade import AutoTradeTask
from backend.models.settings import SimSettings
from backend.services import simulation_trade as st
from backend.services import gold_data
from backend.services import grid_trade


class AutoTradeService:
    # user_id -> {symbol: asyncio.Task}
    _tasks: Dict[int, Dict[str, asyncio.Task]] = {}
    # user_id -> {symbol: bool}
    _running_flags: Dict[int, Dict[str, bool]] = {}
    # user_id -> {symbol: signal_dict}
    _current_signals: Dict[int, Dict[str, Dict]] = {}
    # user_id -> {symbol: float}  # per-task virtual cash balance
    _task_cash: Dict[int, Dict[str, float]] = {}
    # user_id -> {symbol: float}  # per-task cumulative realized P&L
    _task_pnl: Dict[int, Dict[str, float]] = {}
    # user_id -> {symbol: dict}  # per-task position {shares, avg_cost}
    _task_positions: Dict[int, Dict[str, Dict[str, Any]]] = {}
    # user_id -> {symbol: str}  # per-task name (from first trade or lookup)
    _task_names: Dict[int, Dict[str, str]] = {}

    @classmethod
    def _ensure_user_flags(cls, user_id: int):
        if user_id not in cls._running_flags:
            cls._running_flags[user_id] = {}
        if user_id not in cls._current_signals:
            cls._current_signals[user_id] = {}
        if user_id not in cls._tasks:
            cls._tasks[user_id] = {}
        if user_id not in cls._task_cash:
            cls._task_cash[user_id] = {}
        if user_id not in cls._task_pnl:
            cls._task_pnl[user_id] = {}
        if user_id not in cls._task_positions:
            cls._task_positions[user_id] = {}
        if user_id not in cls._task_names:
            cls._task_names[user_id] = {}

    @classmethod
    def is_task_running(cls, user_id: int, symbol: str) -> bool:
        return (
            user_id in cls._tasks
            and symbol in cls._tasks[user_id]
            and cls._tasks[user_id][symbol] is not None
        )

    @classmethod
    async def add_task(cls, user_id: int, symbol: str, config: dict) -> Dict[str, Any]:
        """Add or update a task config (does not start it)"""
        cfg = {
            "strategy": config.get("strategy", "grid"),
            "grid_count": config.get("grid_count", 10),
            "grid_spread": config.get("grid_spread", 0.10),
            "base_ma_key": config.get("base_ma_key", "MA20"),
            "macd_ma_key": config.get("macd_ma_key"),
            "position_size": config.get("position_size", 1.0),
            "check_interval": config.get("check_interval", 30),
            "allocated_funds": config.get("allocated_funds", 0),
            "enabled": False,
            "last_check": None,
            "last_signal": None,
        }
        AutoTradeTask.upsert(user_id, symbol, cfg)
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        return {"success": True, "task": task}

    @classmethod
    async def start_task(cls, user_id: int, symbol: str) -> Dict[str, Any]:
        """Start a single task"""
        if cls.is_task_running(user_id, symbol):
            return {"success": False, "error": f"{symbol} 自动交易已在运行"}

        task_config = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not task_config:
            return {"success": False, "error": f"任务 {symbol} 不存在"}

        portfolio = st.get_portfolio(user_id)
        if portfolio is None:
            st.reset_portfolio(user_id, 100000.0)

        cls._ensure_user_flags(user_id)
        cls._running_flags[user_id][symbol] = True
        # Restore from DB or initialize
        db_cash = task_config.get("task_cash", 0)
        cls._task_cash[user_id][symbol] = db_cash if db_cash > 0 else task_config.get("allocated_funds", 0)
        cls._task_pnl[user_id][symbol] = task_config.get("task_pnl", 0)
        # Restore position from DB
        pos = {"shares": task_config.get("position_shares", 0), "avg_cost": task_config.get("position_avg_cost", 0)}
        if user_id not in cls._task_positions:
            cls._task_positions[user_id] = {}
        cls._task_positions[user_id][symbol] = pos
        # Restore name
        if task_config.get("task_name"):
            cls._task_names[user_id][symbol] = task_config["task_name"]
        loop_task = asyncio.create_task(cls._run_loop(user_id, symbol))
        cls._tasks[user_id][symbol] = loop_task
        AutoTradeTask.update_enabled(user_id, symbol, True)

        return {"success": True, "message": f"{symbol} 自动交易已启动", "task": task_config}

    @classmethod
    async def stop_task(cls, user_id: int, symbol: str) -> Dict[str, Any]:
        """Stop a single task"""
        if not cls.is_task_running(user_id, symbol):
            return {"success": False, "error": f"{symbol} 自动交易未在运行"}

        cls._running_flags[user_id][symbol] = False
        loop_task = cls._tasks[user_id].get(symbol)
        if loop_task:
            loop_task.cancel()
            try:
                await loop_task
            except asyncio.CancelledError:
                pass
        cls._tasks[user_id][symbol] = None
        AutoTradeTask.update_enabled(user_id, symbol, False)

        return {"success": True, "message": f"{symbol} 自动交易已停止"}

    @classmethod
    async def start_all_tasks(cls, user_id: int) -> Dict[str, Any]:
        """Start all tasks for a user"""
        tasks = AutoTradeTask.find_by_user(user_id)
        started = []
        for t in tasks:
            if not cls.is_task_running(user_id, t["symbol"]):
                result = await cls.start_task(user_id, t["symbol"])
                if result.get("success"):
                    started.append(t["symbol"])
        return {"success": True, "started": started}

    @classmethod
    async def stop_all_tasks(cls, user_id: int) -> Dict[str, Any]:
        """Stop all tasks for a user"""
        symbols = list(cls._tasks.get(user_id, {}).keys())
        stopped = []
        for sym in symbols:
            if cls.is_task_running(user_id, sym):
                await cls.stop_task(user_id, sym)
                stopped.append(sym)
        return {"success": True, "stopped": stopped}

    @classmethod
    async def delete_task(cls, user_id: int, symbol: str) -> Dict[str, Any]:
        """Delete a task (must stop first)"""
        if cls.is_task_running(user_id, symbol):
            await cls.stop_task(user_id, symbol)
        AutoTradeTask.delete_task(user_id, symbol)
        cls._ensure_user_flags(user_id)
        cls._current_signals[user_id].pop(symbol, None)
        return {"success": True, "message": f"{symbol} 任务已删除"}

    @classmethod
    def update_task_config(cls, user_id: int, symbol: str, config: dict) -> Dict[str, Any]:
        """Update task config (existing task only, does not restart)"""
        existing = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not existing:
            return {"success": False, "error": f"任务 {symbol} 不存在"}

        updated = {**existing, **config}
        AutoTradeTask.upsert(user_id, symbol, updated)
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        return {"success": True, "task": task}

    @classmethod
    def get_all_status(cls, user_id: int) -> Dict[str, Any]:
        """Get all tasks status for a user"""
        tasks = AutoTradeTask.find_by_user(user_id)
        result = []
        for t in tasks:
            running = cls.is_task_running(user_id, t["symbol"])
            signal = cls._current_signals.get(user_id, {}).get(t["symbol"])
            result.append({
                "symbol": t["symbol"],
                "running": running,
                "task": t,
                "signal": signal,
                "task_cash": cls._task_cash.get(user_id, {}).get(t["symbol"], t.get("task_cash", t.get("allocated_funds", 0))),
                "task_pnl": cls._task_pnl.get(user_id, {}).get(t["symbol"], t.get("task_pnl", 0)),
                "task_position": cls._task_positions.get(user_id, {}).get(t["symbol"], {
                    "shares": t.get("position_shares", 0),
                    "avg_cost": t.get("position_avg_cost", 0),
                }),
                "task_name": cls._task_names.get(user_id, {}).get(t["symbol"], t.get("task_name", t["symbol"])),
                "unrealized_pnl": t.get("unrealized_pnl", 0),
            })
        return result

    @classmethod
    async def _run_loop(cls, user_id: int, symbol: str) -> None:
        while cls._running_flags.get(user_id, {}).get(symbol, False):
            try:
                await cls._check_and_trade(user_id, symbol)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[AutoTrade] {user_id}/{symbol} loop error: {e}")

            task_cfg = AutoTradeTask.find_by_symbol(user_id, symbol)
            interval = task_cfg["check_interval"] if task_cfg else 30
            await asyncio.sleep(interval)

    @classmethod
    def _is_trading_time(cls) -> bool:
        """判断当前是否为交易时间（工作日9:30-11:30, 13:00-15:00）"""
        now = datetime.now()
        if now.weekday() >= 5:  # Saturday, Sunday
            return False
        hour, minute = now.hour, now.minute
        # 9:30-11:30
        if (hour == 9 and minute >= 30) or (9 < hour < 11) or (hour == 11 and minute <= 30):
            return True
        # 13:00-15:00
        if (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
            return True
        return False

    @classmethod
    async def _check_and_trade(cls, user_id: int, symbol: str) -> None:
        if not cls._is_trading_time():
            return

        task_cfg = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not task_cfg:
            return

        grid_count = task_cfg.get("grid_count", 10)
        grid_spread = task_cfg.get("grid_spread", 0.10)
        base_ma_key = task_cfg.get("base_ma_key", "MA20")
        macd_ma_key = task_cfg.get("macd_ma_key")
        position_size = task_cfg.get("position_size", 1.0)

        try:
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

            cls._current_signals[user_id][symbol] = signal

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            AutoTradeTask.update_last_check(user_id, symbol, now_str, signal.get("signal"))

            # Update unrealized pnl every cycle
            close = float(latest["收盘"])
            cur_pos = cls._task_positions.get(user_id, {}).get(symbol, {"shares": 0, "avg_cost": 0})
            unrealized = (close - cur_pos["avg_cost"]) * cur_pos["shares"] if cur_pos["shares"] > 0 else 0
            AutoTradeTask.update_runtime(
                user_id, symbol,
                task_cash=cls._task_cash.get(user_id, {}).get(symbol, 0),
                task_pnl=cls._task_pnl.get(user_id, {}).get(symbol, 0),
                position_shares=cur_pos["shares"],
                position_avg_cost=cur_pos["avg_cost"],
                unrealized_pnl=unrealized,
                task_name=cls._task_names.get(user_id, {}).get(symbol),
            )

            if signal["signal"] not in ("买入", "卖出"):
                return

            close = float(latest["收盘"])
            trade_name = latest.get("名称", symbol)
            if not trade_name or trade_name == symbol:
                trade_name = symbol
            cls._task_names[user_id][symbol] = trade_name

            # 根据网格持仓比例计算目标持仓市值
            position_ratio = signal.get("position_ratio", 0.5)
            allocated_funds = task_cfg.get("allocated_funds", 0)
            target_market_value = allocated_funds * position_ratio
            task_pos = cls._task_positions.get(user_id, {}).get(symbol, {"shares": 0, "avg_cost": 0})
            current_market_value = task_pos["shares"] * close
            value_diff = target_market_value - current_market_value

            settings = SimSettings.get(symbol)
            commission_rate = settings.get("commission_rate", 0.0003)
            min_commission = settings.get("min_commission", 5.0)
            stamp_tax_rate = settings.get("stamp_tax_rate", 0.001)
            transfer_fee_rate = settings.get("transfer_fee_rate", 0.00002)

            # 价值差距小于1格的价值就不操作
            step_value = close * (signal.get("step_pct", 1.0) / 100) * 100
            if abs(value_diff) < step_value:
                return

            if value_diff > 0:
                # 需要买入：目标持仓 > 当前持仓
                buy_amount = value_diff
                shares = int(round(buy_amount / close / 100)) * 100
                if shares < 100:
                    return
                amount = close * shares
                commission_est = max(amount * commission_rate, min_commission)
                task_cash = cls._task_cash[user_id].get(symbol, 0)
                if task_cash < (amount + commission_est):
                    return
                cls._task_cash[user_id][symbol] -= (amount + commission_est)
                total_cost = task_pos["avg_cost"] * task_pos["shares"] + amount
                task_pos["shares"] += shares
                task_pos["avg_cost"] = total_cost / task_pos["shares"] if task_pos["shares"] > 0 else close
                if user_id not in cls._task_positions:
                    cls._task_positions[user_id] = {}
                cls._task_positions[user_id][symbol] = task_pos
                result = st.execute_trade(user_id, "buy", symbol, trade_name, close, shares, trade_type="auto")
                action_str = "买入"
            else:
                # 需要卖出：当前持仓 > 目标持仓
                sell_amount = abs(value_diff)
                shares = int(round(sell_amount / close / 100)) * 100
                if shares < 100 or task_pos["shares"] < 100:
                    return
                shares = min(shares, task_pos["shares"])
                shares = (shares // 100) * 100
                if shares < 100:
                    return
                result = st.execute_trade(user_id, "sell", symbol, trade_name, close, shares, trade_type="auto")
                if result.get("success"):
                    sell_proceeds = close * shares
                    stamp_tax = sell_proceeds * stamp_tax_rate
                    transfer_fee = sell_proceeds * transfer_fee_rate if symbol.startswith("sh") else 0
                    net_proceeds = sell_proceeds - max(sell_proceeds * commission_rate, min_commission) - stamp_tax - transfer_fee
                    cls._task_cash[user_id][symbol] += net_proceeds
                    pnl = (close - task_pos["avg_cost"]) * shares
                    cls._task_pnl[user_id][symbol] = cls._task_pnl.get(user_id, {}).get(symbol, 0) + pnl
                    task_pos["shares"] -= shares
                    if task_pos["shares"] == 0:
                        task_pos["avg_cost"] = 0
                    if user_id not in cls._task_positions:
                        cls._task_positions[user_id] = {}
                    cls._task_positions[user_id][symbol] = task_pos
                action_str = "卖出"

            if result.get("success"):
                print(f"[AutoTrade] {user_id}/{symbol} {action_str} {shares} shares at {close:.4f}, target_ratio={position_ratio:.2f}, diff={value_diff:.2f}")
                cur_task_pos = cls._task_positions.get(user_id, {}).get(symbol, {"shares": 0, "avg_cost": 0})
                AutoTradeTask.update_runtime(
                    user_id, symbol,
                    task_cash=cls._task_cash.get(user_id, {}).get(symbol, 0),
                    task_pnl=cls._task_pnl.get(user_id, {}).get(symbol, 0),
                    position_shares=cur_task_pos["shares"],
                    position_avg_cost=cur_task_pos["avg_cost"],
                    task_name=cls._task_names.get(user_id, {}).get(symbol),
                )

        except Exception as e:
            print(f"[AutoTrade] {user_id}/{symbol} trade error: {e}")
