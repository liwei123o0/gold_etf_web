"""Auto Trade Service - DB-driven task management

所有任务状态以数据库为准，不再维护内存中的 asyncio.Task。
启动/停止任务仅修改 DB 中的 enabled 字段，
实际的交易检查由 AutoTradeScheduler 统一调度执行。
"""
from typing import Dict, Any

from backend.models.auto_trade import AutoTradeTask
from backend.services.auto_trade_scheduler import AutoTradeScheduler


class AutoTradeService:

    @classmethod
    def is_task_running(cls, user_id: int, symbol: str) -> bool:
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not task:
            return False
        return task.get("enabled", False) and AutoTradeScheduler.is_running()

    @classmethod
    async def add_task(cls, user_id: int, symbol: str, config: dict) -> Dict[str, Any]:
        position_shares = config.get("position_shares", 0) or 0
        position_avg_cost = config.get("position_avg_cost", 0) or 0
        allocated_funds = config.get("allocated_funds", 0) or 0
        position_value = position_shares * position_avg_cost if position_shares > 0 and position_avg_cost > 0 else 0
        task_cash = allocated_funds - position_value

        cfg = {
            "strategy": config.get("strategy", "grid"),
            "grid_count": config.get("grid_count", 10),
            "grid_spread": config.get("grid_spread", 0.10),
            "base_ma_key": config.get("base_ma_key", "MA20"),
            "macd_ma_key": config.get("macd_ma_key"),
            "position_size": config.get("position_size", 1.0),
            "check_interval": config.get("check_interval", 30),
            "allocated_funds": allocated_funds,
            "enabled": False,
            "last_check": None,
            "last_signal": None,
            "task_cash": task_cash,
            "task_pnl": 0,
            "position_shares": position_shares,
            "position_avg_cost": position_avg_cost,
            "unrealized_pnl": 0,
            "task_name": config.get("task_name", symbol),
            "stop_loss_pct": config.get("stop_loss_pct", -5.0),
            "take_profit_pct": config.get("take_profit_pct", 10.0),
            "trend_ma_key": config.get("trend_ma_key"),
            "dynamic_interval": config.get("dynamic_interval", False),
            "cooldown_seconds": config.get("cooldown_seconds", 60),
            "max_daily_trades": config.get("max_daily_trades", 50),
        }
        AutoTradeTask.upsert(user_id, symbol, cfg)
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        return {"success": True, "task": task}

    @classmethod
    async def start_task(cls, task_id: int) -> Dict[str, Any]:
        task_config = AutoTradeTask.find_by_id(task_id)
        if not task_config:
            return {"success": False, "error": f"任务 {task_id} 不存在"}

        user_id = task_config["user_id"]
        symbol = task_config["symbol"]

        if task_config.get("enabled", False) and AutoTradeScheduler.is_running():
            return {"success": False, "error": f"{symbol} 自动交易已在运行"}

        from backend.services import simulation_trade as st
        portfolio = st.get_portfolio(user_id)
        if portfolio is None:
            st.reset_portfolio(user_id, 100000.0)

        db_cash = task_config.get("task_cash", 0)
        if db_cash <= 0:
            AutoTradeTask.update_runtime(
                task_id,
                task_cash=task_config.get("allocated_funds", 0),
                task_pnl=0,
                position_shares=0,
                position_avg_cost=0,
                unrealized_pnl=0,
                task_name=task_config.get("task_name", symbol),
            )

        AutoTradeTask.update_enabled(task_id, True)

        if not AutoTradeScheduler.is_running():
            await AutoTradeScheduler.start()

        return {"success": True, "message": f"{symbol} 自动交易已启动", "task": task_config}

    @classmethod
    async def stop_task(cls, task_id: int) -> Dict[str, Any]:
        task_config = AutoTradeTask.find_by_id(task_id)
        if not task_config:
            return {"success": False, "error": f"任务 {task_id} 不存在"}

        AutoTradeTask.update_enabled(task_id, False)
        symbol = task_config.get("symbol", "")
        return {"success": True, "message": f"{symbol} 自动交易已停止"}

    @classmethod
    async def start_all_tasks(cls, user_id: int) -> Dict[str, Any]:
        tasks = AutoTradeTask.find_by_user(user_id)
        started = []
        for t in tasks:
            if not t.get("enabled", False):
                result = await cls.start_task(t["id"])
                if result.get("success"):
                    started.append(t["symbol"])
        return {"success": True, "started": started}

    @classmethod
    async def stop_all_tasks(cls, user_id: int) -> Dict[str, Any]:
        tasks = AutoTradeTask.find_by_user(user_id)
        stopped = []
        for t in tasks:
            if t.get("enabled", False):
                AutoTradeTask.update_enabled(t["id"], False)
                stopped.append(t["symbol"])
        return {"success": True, "stopped": stopped}

    @classmethod
    async def delete_task(cls, task_id: int) -> Dict[str, Any]:
        task = AutoTradeTask.find_by_id(task_id)
        if task and task.get("enabled", False):
            AutoTradeTask.update_enabled(task_id, False)
        AutoTradeTask.delete_task(task_id)
        symbol = task.get("symbol", "") if task else ""
        return {"success": True, "message": f"{symbol} 任务已删除"}

    @classmethod
    def update_task_config(cls, task_id: int, config: dict) -> Dict[str, Any]:
        existing = AutoTradeTask.find_by_id(task_id)
        if not existing:
            return {"success": False, "error": f"任务 {task_id} 不存在"}

        updated = {**existing, **config}
        AutoTradeTask.upsert(existing["user_id"], existing["symbol"], updated)
        task = AutoTradeTask.find_by_id(task_id)
        return {"success": True, "task": task}

    @classmethod
    def get_all_status(cls, user_id: int) -> Dict[str, Any]:
        return AutoTradeScheduler.get_status(user_id)
