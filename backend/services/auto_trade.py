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
            "task_cash": config.get("allocated_funds", 0),
            "task_pnl": 0,
            "position_shares": 0,
            "position_avg_cost": 0,
            "unrealized_pnl": 0,
            "task_name": config.get("task_name", symbol),
        }
        AutoTradeTask.upsert(user_id, symbol, cfg)
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        return {"success": True, "task": task}

    @classmethod
    async def start_task(cls, user_id: int, symbol: str) -> Dict[str, Any]:
        task_config = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not task_config:
            return {"success": False, "error": f"任务 {symbol} 不存在"}

        if task_config.get("enabled", False) and AutoTradeScheduler.is_running():
            return {"success": False, "error": f"{symbol} 自动交易已在运行"}

        from backend.services import simulation_trade as st
        portfolio = st.get_portfolio(user_id)
        if portfolio is None:
            st.reset_portfolio(user_id, 100000.0)

        db_cash = task_config.get("task_cash", 0)
        if db_cash <= 0:
            AutoTradeTask.update_runtime(
                user_id, symbol,
                task_cash=task_config.get("allocated_funds", 0),
                task_pnl=0,
                position_shares=0,
                position_avg_cost=0,
                unrealized_pnl=0,
                task_name=task_config.get("task_name", symbol),
            )

        AutoTradeTask.update_enabled(user_id, symbol, True)

        if not AutoTradeScheduler.is_running():
            await AutoTradeScheduler.start()

        return {"success": True, "message": f"{symbol} 自动交易已启动", "task": task_config}

    @classmethod
    async def stop_task(cls, user_id: int, symbol: str) -> Dict[str, Any]:
        task_config = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not task_config:
            return {"success": False, "error": f"任务 {symbol} 不存在"}

        AutoTradeTask.update_enabled(user_id, symbol, False)
        return {"success": True, "message": f"{symbol} 自动交易已停止"}

    @classmethod
    async def start_all_tasks(cls, user_id: int) -> Dict[str, Any]:
        tasks = AutoTradeTask.find_by_user(user_id)
        started = []
        for t in tasks:
            if not t.get("enabled", False):
                result = await cls.start_task(user_id, t["symbol"])
                if result.get("success"):
                    started.append(t["symbol"])
        return {"success": True, "started": started}

    @classmethod
    async def stop_all_tasks(cls, user_id: int) -> Dict[str, Any]:
        tasks = AutoTradeTask.find_by_user(user_id)
        stopped = []
        for t in tasks:
            if t.get("enabled", False):
                AutoTradeTask.update_enabled(user_id, t["symbol"], False)
                stopped.append(t["symbol"])
        return {"success": True, "stopped": stopped}

    @classmethod
    async def delete_task(cls, user_id: int, symbol: str) -> Dict[str, Any]:
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        if task and task.get("enabled", False):
            AutoTradeTask.update_enabled(user_id, symbol, False)
        AutoTradeTask.delete_task(user_id, symbol)
        return {"success": True, "message": f"{symbol} 任务已删除"}

    @classmethod
    def update_task_config(cls, user_id: int, symbol: str, config: dict) -> Dict[str, Any]:
        existing = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not existing:
            return {"success": False, "error": f"任务 {symbol} 不存在"}

        updated = {**existing, **config}
        AutoTradeTask.upsert(user_id, symbol, updated)
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        return {"success": True, "task": task}

    @classmethod
    def get_all_status(cls, user_id: int) -> Dict[str, Any]:
        return AutoTradeScheduler.get_status(user_id)
