"""
自动交易服务模块 - 基于数据库驱动的任务管理

本模块提供自动交易任务的管理功能，包括：
- 任务生命周期管理：创建、启动、停止、删除任务
- 任务状态查询：获取任务运行状态
- 配置更新：修改任务参数

设计原则：
- 所有任务状态以数据库为准，不再维护内存中的 asyncio.Task
- 启动/停止任务仅修改数据库中的 enabled 字段
- 实际的交易检查由 AutoTradeScheduler 统一调度执行
"""
from typing import Dict, Any

from backend.models.auto_trade import AutoTradeTask
from backend.services.auto_trade_scheduler import AutoTradeScheduler


class AutoTradeService:
    """
    自动交易服务类
    
    提供自动交易任务的 CRUD 操作和生命周期管理。
    所有方法都是类方法，无需实例化即可调用。
    """

    @classmethod
    def is_task_running(cls, user_id: int, symbol: str) -> bool:
        """
        检查指定股票的自动交易任务是否正在运行
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            
        Returns:
            bool: 任务是否正在运行（enabled=True 且调度器正在运行）
        """
        task = AutoTradeTask.find_by_symbol(user_id, symbol)
        if not task:
            return False
        return task.get("enabled", False) and AutoTradeScheduler.is_running()

    @classmethod
    async def add_task(cls, user_id: int, symbol: str, config: dict) -> Dict[str, Any]:
        """
        添加新的自动交易任务
        
        根据配置创建新的自动交易任务，任务默认处于停止状态（enabled=False）。
        如果该股票已有任务，则更新现有任务配置。
        
        Args:
            user_id: 用户ID
            symbol: 股票代码
            config: 任务配置字典，包含以下字段：
                - strategy: 策略类型（grid/ma_trend等）
                - grid_count: 网格数量
                - grid_spread: 网格间距百分比
                - base_ma_key: 基准均线周期
                - allocated_funds: 分配资金
                - position_shares: 初始持仓数量
                - position_avg_cost: 初始持仓成本
                - stop_loss_pct: 止损百分比
                - take_profit_pct: 止盈百分比
                
        Returns:
            dict: 包含 success 和 task 字段的结果
        """
        # 计算任务可用现金
        position_shares = config.get("position_shares", 0) or 0
        position_avg_cost = config.get("position_avg_cost", 0) or 0
        allocated_funds = config.get("allocated_funds", 0) or 0
        position_value = position_shares * position_avg_cost if position_shares > 0 and position_avg_cost > 0 else 0
        task_cash = allocated_funds - position_value

        # 构建任务配置
        cfg = {
            "strategy": config.get("strategy", "grid"),
            "grid_count": config.get("grid_count", 10),
            "grid_spread": config.get("grid_spread", 0.10),
            "base_ma_key": config.get("base_ma_key", "MA20"),
            "macd_ma_key": config.get("macd_ma_key"),
            "position_size": config.get("position_size", 1.0),
            "check_interval": config.get("check_interval", 30),
            "allocated_funds": allocated_funds,
            "enabled": False,  # 新建任务默认停止
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
        """
        启动指定的自动交易任务
        
        将任务的 enabled 字段设为 True，并确保调度器正在运行。
        如果用户没有模拟账户，会自动创建一个初始资金为 10 万的账户。
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 包含以下字段的结果
                - success: 是否成功
                - error: 错误信息（失败时）
                - message: 成功消息
                - task: 任务配置信息
        """
        task_config = AutoTradeTask.find_by_id(task_id)
        if not task_config:
            return {"success": False, "error": f"任务 {task_id} 不存在"}

        user_id = task_config["user_id"]
        symbol = task_config["symbol"]

        # 检查任务是否已在运行
        if task_config.get("enabled", False) and AutoTradeScheduler.is_running():
            return {"success": False, "error": f"{symbol} 自动交易已在运行"}

        # 确保用户有模拟账户
        from backend.services import simulation_trade as st
        portfolio = st.get_portfolio(user_id)
        if portfolio is None:
            st.reset_portfolio(user_id, 100000.0)

        # 检查任务现金是否有效，无效则重置
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

        # 启用任务
        AutoTradeTask.update_enabled(task_id, True)

        # 确保调度器正在运行
        if not AutoTradeScheduler.is_running():
            await AutoTradeScheduler.start()

        return {"success": True, "message": f"{symbol} 自动交易已启动", "task": task_config}

    @classmethod
    async def stop_task(cls, task_id: int) -> Dict[str, Any]:
        """
        停止指定的自动交易任务
        
        将任务的 enabled 字段设为 False，任务将不再被调度器执行。
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 包含 success 和 message 字段的结果
        """
        task_config = AutoTradeTask.find_by_id(task_id)
        if not task_config:
            return {"success": False, "error": f"任务 {task_id} 不存在"}

        AutoTradeTask.update_enabled(task_id, False)
        symbol = task_config.get("symbol", "")
        return {"success": True, "message": f"{symbol} 自动交易已停止"}

    @classmethod
    async def start_all_tasks(cls, user_id: int) -> Dict[str, Any]:
        """
        启动用户的所有自动交易任务
        
        遍历用户的所有任务，启动处于停止状态的任务。
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 包含 success 和 started 字段的结果
                - started: 已启动的任务股票代码列表
        """
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
        """
        停止用户的所有自动交易任务
        
        遍历用户的所有任务，停止处于运行状态的任务。
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 包含 success 和 stopped 字段的结果
                - stopped: 已停止的任务股票代码列表
        """
        tasks = AutoTradeTask.find_by_user(user_id)
        stopped = []
        for t in tasks:
            if t.get("enabled", False):
                AutoTradeTask.update_enabled(t["id"], False)
                stopped.append(t["symbol"])
        return {"success": True, "stopped": stopped}

    @classmethod
    async def delete_task(cls, task_id: int) -> Dict[str, Any]:
        """
        删除指定的自动交易任务
        
        先停止任务（如果正在运行），然后从数据库中删除任务记录。
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 包含 success 和 message 字段的结果
        """
        task = AutoTradeTask.find_by_id(task_id)
        if task and task.get("enabled", False):
            AutoTradeTask.update_enabled(task_id, False)
        AutoTradeTask.delete_task(task_id)
        symbol = task.get("symbol", "") if task else ""
        return {"success": True, "message": f"{symbol} 任务已删除"}

    @classmethod
    def update_task_config(cls, task_id: int, config: dict) -> Dict[str, Any]:
        """
        更新任务的配置参数
        
        合并现有配置和新配置，更新任务记录。
        
        Args:
            task_id: 任务ID
            config: 新的配置参数字典
            
        Returns:
            dict: 包含 success 和 task 字段的结果
        """
        existing = AutoTradeTask.find_by_id(task_id)
        if not existing:
            return {"success": False, "error": f"任务 {task_id} 不存在"}

        # 合并配置
        updated = {**existing, **config}
        AutoTradeTask.upsert(existing["user_id"], existing["symbol"], updated)
        task = AutoTradeTask.find_by_id(task_id)
        return {"success": True, "task": task}

    @classmethod
    def get_all_status(cls, user_id: int) -> Dict[str, Any]:
        """
        获取用户所有自动交易任务的状态
        
        从调度器获取任务的运行状态信息。
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 包含各任务状态的结果
        """
        return AutoTradeScheduler.get_status(user_id)
