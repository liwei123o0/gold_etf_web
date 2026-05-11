"""
自动交易任务数据模型

定义自动交易任务的 ORM 模型及业务操作类，
支持网格交易、均线趋势等策略的自动执行，
包括任务创建、更新、启停控制、冷却检查、回撤监控等功能。
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, func, text, UniqueConstraint

from .db import Base, get_session
from ..utils.timezone import china_now_naive


class AutoTradeTaskModel(Base):
    """
    自动交易任务 ORM 模型

    对应数据库表 auto_trade_tasks，存储自动交易任务的完整配置和运行状态，
    包括策略参数、资金分配、持仓信息、风控参数和运行时状态等。
    唯一约束：(user_id, symbol, strategy)，同一用户同一标的不允许重复策略。
    """
    __tablename__ = "auto_trade_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "strategy", name="uq_user_symbol_strategy"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)                     # 任务ID，主键自增
    user_id = Column(Integer, nullable=False)                                      # 用户ID
    symbol = Column(String, nullable=False)                                        # 股票代码
    strategy = Column(String, nullable=False, default="grid")                      # 策略类型(grid网格/ma_trend均线趋势)
    grid_count = Column(Integer, default=10)                                       # 网格数量
    grid_spread = Column(Numeric, default=0.10)                                    # 网格间距(百分比)
    base_ma_key = Column(String, default="MA20")                                   # 基础均线周期(MA5/MA10/MA20等)
    macd_ma_key = Column(String, nullable=True)                                    # MACD均线周期
    position_size = Column(Numeric, default=1.0)                                   # 仓位大小(0.0-1.0)
    check_interval = Column(Integer, default=30)                                   # 检查间隔(秒)
    allocated_funds = Column(Numeric, default=0)                                   # 分配资金总额
    enabled = Column(Boolean, nullable=False, default=False)                       # 是否启用
    last_check = Column(DateTime, nullable=True)                                   # 最后检查时间
    last_signal = Column(String, nullable=True)                                    # 最后信号
    task_cash = Column(Numeric, default=0)                                         # 任务可用资金
    task_pnl = Column(Numeric, default=0)                                          # 任务累计盈亏
    position_shares = Column(Integer, default=0)                                   # 持仓数量（股）
    position_avg_cost = Column(Numeric, default=0)                                 # 持仓平均成本
    task_name = Column(String, default="")                                         # 任务名称
    unrealized_pnl = Column(Numeric, default=0)                                    # 浮动盈亏
    stop_loss_pct = Column(Numeric, default=-5.0)                                  # 止损百分比(负数，如-5.0表示跌5%止损)
    take_profit_pct = Column(Numeric, default=10.0)                                # 止盈百分比(正数，如10.0表示涨10%止盈)
    trend_ma_key = Column(String, nullable=True)                                   # 趋势均线周期
    dynamic_interval = Column(Boolean, default=False)                              # 是否启用动态间隔
    last_trade_time = Column(DateTime, nullable=True)                              # 最后交易时间
    last_trade_direction = Column(String, nullable=True)                           # 最后交易方向(买入/卖出)
    trade_count_today = Column(Integer, default=0)                                 # 今日交易次数
    last_trade_date = Column(String, nullable=True)                                # 最后交易日期(格式: YYYYMMDD)
    consecutive_signals = Column(Integer, default=0)                               # 连续信号计数(用于信号确认)
    cooldown_seconds = Column(Integer, default=60)                                 # 冷却时间(秒)，两次交易间的最小间隔
    max_daily_trades = Column(Integer, default=50)                                 # 每日最大交易次数
    max_drawdown_pct = Column(Numeric, default=-15.0)                              # 最大回撤阈值(%)，负数，触发后暂停交易
    peak_value = Column(Numeric, default=0)                                        # 历史净值峰值(用于回撤计算)
    consecutive_losses = Column(Integer, default=0)                                # 连续亏损次数(影响冷却时间)
    use_multi_factor = Column(Boolean, default=False)                              # 是否启用多因子评分增强
    adaptive_strategy = Column(Boolean, default=False)                             # 是否启用自适应策略切换
    created_at = Column(DateTime, default=china_now_naive)                         # 创建时间
    updated_at = Column(DateTime, default=china_now_naive, onupdate=china_now_naive)  # 更新时间


class AutoTradeTask:
    """
    自动交易任务业务操作类

    提供自动交易任务的完整生命周期管理，包括：
    - 任务的查询（按用户、标的、启用状态等）
    - 任务的新增/更新（upsert）
    - 任务的启停控制
    - 运行时状态更新（资金、持仓、盈亏等）
    - 交易记录与冷却检查
    - 回撤监控与连续亏损追踪
    - 数据库表结构迁移
    """

    @classmethod
    def from_row(cls, row):
        """
        将 ORM 行对象转换为字典格式

        Args:
            row: AutoTradeTaskModel ORM 行对象，若为 None 则返回 None

        Returns:
            dict | None: 包含任务完整配置和运行状态的字典；
                         若 row 为 None 则返回 None
        """
        if row is None:
            return None
        return {
            "id": row.id,                                                          # 任务ID
            "user_id": row.user_id,                                                # 用户ID
            "symbol": row.symbol,                                                  # 股票代码
            "strategy": row.strategy,                                              # 策略类型
            "grid_count": row.grid_count,                                          # 网格数量
            "grid_spread": float(row.grid_spread),                                 # 网格间距
            "base_ma_key": row.base_ma_key,                                        # 基础均线周期
            "macd_ma_key": row.macd_ma_key,                                        # MACD均线周期
            "position_size": float(row.position_size),                             # 仓位大小
            "check_interval": row.check_interval,                                  # 检查间隔
            "allocated_funds": float(row.allocated_funds or 0),                    # 分配资金总额
            "enabled": bool(row.enabled),                                          # 是否启用
            "last_check": row.last_check,                                          # 最后检查时间
            "last_signal": row.last_signal,                                        # 最后信号
            "task_cash": float(row.task_cash or 0),                                # 任务可用资金
            "task_pnl": float(row.task_pnl or 0),                                  # 任务累计盈亏
            "position_shares": row.position_shares or 0,                           # 持仓数量
            "position_avg_cost": float(row.position_avg_cost or 0),                # 持仓平均成本
            "task_name": row.task_name or row.symbol,                              # 任务名称
            "unrealized_pnl": float(row.unrealized_pnl or 0),                      # 浮动盈亏
            "stop_loss_pct": float(getattr(row, 'stop_loss_pct', -5.0) or -5.0),   # 止损百分比
            "take_profit_pct": float(getattr(row, 'take_profit_pct', 10.0) or 10.0),  # 止盈百分比
            "trend_ma_key": getattr(row, 'trend_ma_key', None),                    # 趋势均线周期
            "dynamic_interval": bool(getattr(row, 'dynamic_interval', False)),     # 是否启用动态间隔
            "last_trade_time": getattr(row, 'last_trade_time', None),              # 最后交易时间
            "last_trade_direction": getattr(row, 'last_trade_direction', None),    # 最后交易方向
            "trade_count_today": getattr(row, 'trade_count_today', 0) or 0,        # 今日交易次数
            "last_trade_date": getattr(row, 'last_trade_date', None),              # 最后交易日期
            "consecutive_signals": getattr(row, 'consecutive_signals', 0) or 0,    # 连续信号计数
            "cooldown_seconds": getattr(row, 'cooldown_seconds', 60) or 60,        # 冷却时间
            "max_daily_trades": getattr(row, 'max_daily_trades', 50) or 50,        # 每日最大交易次数
            "max_drawdown_pct": float(getattr(row, 'max_drawdown_pct', -15.0) or -15.0),  # 最大回撤阈值
            "peak_value": float(getattr(row, 'peak_value', 0) or 0),               # 历史净值峰值
            "consecutive_losses": getattr(row, 'consecutive_losses', 0) or 0,      # 连续亏损次数
            "use_multi_factor": bool(getattr(row, 'use_multi_factor', False)),     # 是否启用多因子评分
            "adaptive_strategy": bool(getattr(row, 'adaptive_strategy', False)),   # 是否启用自适应策略
            "created_at": row.created_at,                                          # 创建时间
            "updated_at": row.updated_at,                                          # 更新时间
        }

    @classmethod
    def find_by_user(cls, user_id):
        """
        根据用户ID查询所有自动交易任务，按创建时间倒序排列

        Args:
            user_id (int): 用户ID

        Returns:
            list[dict]: 任务信息字典列表，按创建时间倒序排列
        """
        with get_session() as session:
            rows = (
                session.query(AutoTradeTaskModel)
                .filter(AutoTradeTaskModel.user_id == user_id)
                .order_by(AutoTradeTaskModel.created_at.desc())
                .all()
            )
            return [cls.from_row(r) for r in rows]

    @classmethod
    def find_by_symbol(cls, user_id, symbol, strategy=None):
        """
        根据用户ID和股票代码查询自动交易任务

        Args:
            user_id (int): 用户ID
            symbol (str): 股票代码
            strategy (str | None): 策略类型，若指定则进一步过滤，默认 None

        Returns:
            dict | None: 任务信息字典，若不存在则返回 None
        """
        with get_session() as session:
            query = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
            )
            if strategy:
                query = query.filter(AutoTradeTaskModel.strategy == strategy)
            row = query.first()
            return cls.from_row(row) if row else None

    @classmethod
    def find_all_enabled(cls):
        """
        查询所有已启用的自动交易任务，按创建时间倒序排列

        Returns:
            list[dict]: 所有已启用任务的信息字典列表
        """
        with get_session() as session:
            rows = (
                session.query(AutoTradeTaskModel)
                .filter(AutoTradeTaskModel.enabled == True)
                .order_by(AutoTradeTaskModel.created_at.desc())
                .all()
            )
            return [cls.from_row(r) for r in rows]

    @classmethod
    def upsert(cls, user_id, symbol, config: dict):
        """
        新增或更新自动交易任务

        若该用户+标的+策略组合已存在则更新配置，否则新增任务。
        更新时会自动计算任务可用资金（分配资金 - 持仓市值）。

        Args:
            user_id (int): 用户ID
            symbol (str): 股票代码
            config (dict): 任务配置字典，可包含以下键：
                - strategy (str): 策略类型
                - grid_count (int): 网格数量
                - grid_spread (float): 网格间距
                - base_ma_key (str): 基础均线周期
                - macd_ma_key (str): MACD均线周期
                - position_size (float): 仓位大小
                - check_interval (int): 检查间隔
                - allocated_funds (float): 分配资金
                - enabled (bool): 是否启用
                - 以及其他风控和运行时参数

        Returns:
            int: 任务的ID
        """
        with get_session() as session:
            existing = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
                AutoTradeTaskModel.strategy == config.get("strategy", "grid"),
            ).first()
            if existing:
                existing.strategy = config.get("strategy", existing.strategy)
                existing.grid_count = config.get("grid_count", existing.grid_count)
                existing.grid_spread = config.get("grid_spread", existing.grid_spread)
                existing.base_ma_key = config.get("base_ma_key", existing.base_ma_key)
                existing.macd_ma_key = config.get("macd_ma_key", existing.macd_ma_key)
                existing.position_size = config.get("position_size", existing.position_size)
                existing.check_interval = config.get("check_interval", existing.check_interval)
                existing.allocated_funds = config.get("allocated_funds", existing.allocated_funds)
                existing.enabled = config.get("enabled", existing.enabled)
                existing.last_check = config.get("last_check", existing.last_check)
                existing.last_signal = config.get("last_signal", existing.last_signal)
                existing.task_pnl = config.get("task_pnl", existing.task_pnl)
                existing.unrealized_pnl = config.get("unrealized_pnl", existing.unrealized_pnl)
                existing.task_name = config.get("task_name", existing.task_name)
                existing.stop_loss_pct = config.get("stop_loss_pct", existing.stop_loss_pct)
                existing.take_profit_pct = config.get("take_profit_pct", existing.take_profit_pct)
                existing.trend_ma_key = config.get("trend_ma_key", existing.trend_ma_key)
                existing.dynamic_interval = config.get("dynamic_interval", existing.dynamic_interval)
                existing.cooldown_seconds = config.get("cooldown_seconds", existing.cooldown_seconds)
                existing.max_daily_trades = config.get("max_daily_trades", existing.max_daily_trades)
                existing.max_drawdown_pct = config.get("max_drawdown_pct", existing.max_drawdown_pct)
                if "peak_value" in config:
                    existing.peak_value = config.get("peak_value", existing.peak_value)
                if "consecutive_losses" in config:
                    existing.consecutive_losses = config.get("consecutive_losses", existing.consecutive_losses)
                existing.use_multi_factor = config.get("use_multi_factor", existing.use_multi_factor)
                existing.adaptive_strategy = config.get("adaptive_strategy", existing.adaptive_strategy)

                if "position_shares" in config or "position_avg_cost" in config:
                    existing.position_shares = config.get("position_shares", existing.position_shares)
                    existing.position_avg_cost = config.get("position_avg_cost", existing.position_avg_cost)
                    position_value = existing.position_shares * existing.position_avg_cost if existing.position_shares > 0 and existing.position_avg_cost > 0 else 0
                    existing.task_cash = existing.allocated_funds - position_value

                existing.updated_at = china_now_naive()
                session.flush()
                return existing.id
            else:
                position_shares = config.get("position_shares", 0)
                position_avg_cost = config.get("position_avg_cost", 0)
                allocated_funds = config.get("allocated_funds", 0)
                position_value = position_shares * position_avg_cost if position_shares > 0 and position_avg_cost > 0 else 0
                task_cash = config.get("task_cash", allocated_funds - position_value)

                model = AutoTradeTaskModel(
                    user_id=user_id,
                    symbol=symbol,
                    strategy=config.get("strategy", "grid"),
                    grid_count=config.get("grid_count", 10),
                    grid_spread=config.get("grid_spread", 0.10),
                    base_ma_key=config.get("base_ma_key", "MA20"),
                    macd_ma_key=config.get("macd_ma_key"),
                    position_size=config.get("position_size", 1.0),
                    check_interval=config.get("check_interval", 30),
                    allocated_funds=allocated_funds,
                    enabled=config.get("enabled", False),
                    last_check=config.get("last_check"),
                    last_signal=config.get("last_signal"),
                    task_cash=task_cash,
                    task_pnl=config.get("task_pnl", 0),
                    position_shares=position_shares,
                    position_avg_cost=position_avg_cost,
                    unrealized_pnl=config.get("unrealized_pnl", 0),
                    stop_loss_pct=config.get("stop_loss_pct", -5.0),
                    take_profit_pct=config.get("take_profit_pct", 10.0),
                    trend_ma_key=config.get("trend_ma_key"),
                    dynamic_interval=config.get("dynamic_interval", False),
                    task_name=config.get("task_name", symbol),
                    max_drawdown_pct=config.get("max_drawdown_pct", -15.0),
                    peak_value=config.get("peak_value", 0),
                    consecutive_losses=config.get("consecutive_losses", 0),
                    use_multi_factor=config.get("use_multi_factor", False),
                    adaptive_strategy=config.get("adaptive_strategy", False),
                    created_at=china_now_naive(),
                    updated_at=china_now_naive(),
                )
                session.add(model)
                session.flush()
                return model.id

    @classmethod
    def update_enabled(cls, task_id, enabled: bool):
        """
        更新任务的启用/禁用状态

        Args:
            task_id (int): 任务ID
            enabled (bool): True 启用，False 禁用
        """
        with get_session() as session:
            existing = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if existing:
                existing.enabled = enabled
                existing.updated_at = china_now_naive()

    @classmethod
    def find_by_id(cls, task_id):
        """
        根据任务ID查询任务信息

        Args:
            task_id (int): 任务ID

        Returns:
            dict | None: 任务信息字典，若不存在则返回 None
        """
        with get_session() as session:
            row = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            return cls.from_row(row) if row else None

    @classmethod
    def update_last_check(cls, task_id, last_signal: str = None):
        """
        更新任务的最后检查时间和最后信号

        Args:
            task_id (int): 任务ID
            last_signal (str | None): 最后信号描述，默认 None
        """
        import logging
        logger = logging.getLogger(__name__)
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if model:
                model.last_check = china_now_naive()
                model.last_signal = last_signal
                model.updated_at = china_now_naive()
            else:
                logger.warning(f"[AutoTrade] update_last_check: 任务不存在 id={task_id}")

    @classmethod
    def update_runtime(cls, task_id, task_cash: float, task_pnl: float,
                       position_shares: int, position_avg_cost: float,
                       unrealized_pnl: float = 0, task_name: str = None):
        """
        更新任务的运行时状态（资金、持仓、盈亏等）

        Args:
            task_id (int): 任务ID
            task_cash (float): 任务可用资金
            task_pnl (float): 任务累计盈亏
            position_shares (int): 持仓数量
            position_avg_cost (float): 持仓平均成本
            unrealized_pnl (float): 浮动盈亏，默认 0
            task_name (str | None): 任务名称，若为 None 则不更新，默认 None
        """
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if model:
                model.task_cash = task_cash
                model.task_pnl = task_pnl
                model.position_shares = position_shares
                model.position_avg_cost = position_avg_cost
                model.unrealized_pnl = unrealized_pnl
                model.updated_at = china_now_naive()
                if task_name is not None:
                    model.task_name = task_name

    @classmethod
    def total_allocated_funds(cls, user_id):
        """
        计算用户所有自动交易任务的分配资金总额

        Args:
            user_id (int): 用户ID

        Returns:
            float: 分配资金总额
        """
        with get_session() as session:
            result = session.query(func.coalesce(func.sum(AutoTradeTaskModel.allocated_funds), 0)).filter(
                AutoTradeTaskModel.user_id == user_id
            ).scalar()
            return float(result)

    @classmethod
    def delete_task(cls, task_id):
        """
        根据任务ID删除自动交易任务

        Args:
            task_id (int): 任务ID
        """
        with get_session() as session:
            session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).delete()

    @classmethod
    def delete_task_by_symbol(cls, user_id, symbol):
        """
        根据用户ID和股票代码删除自动交易任务

        Args:
            user_id (int): 用户ID
            symbol (str): 股票代码
        """
        with get_session() as session:
            session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
            ).delete()

    @classmethod
    def record_trade(cls, task_id, direction: str):
        """
        记录一次交易：更新最后交易时间、方向、今日计数

        若交易日期与上次不同，则重置今日交易计数。
        同时将连续信号计数归零。

        Args:
            task_id (int): 任务ID
            direction (str): 交易方向(买入/卖出)
        """
        today_str = china_now_naive().strftime("%Y%m%d")
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if model:
                if getattr(model, 'last_trade_date', None) != today_str:
                    model.trade_count_today = 0
                    model.last_trade_date = today_str
                model.last_trade_time = china_now_naive()
                model.last_trade_direction = direction
                model.trade_count_today = (model.trade_count_today or 0) + 1
                model.consecutive_signals = 0
                model.updated_at = china_now_naive()

    @classmethod
    def is_in_cooldown(cls, task_id) -> bool:
        """
        检查任务是否处于冷却期

        冷却时间根据连续亏损次数动态调整：
        - 连续亏损 >= 3 次：冷却 300 秒
        - 连续亏损 >= 2 次：冷却 180 秒
        - 连续亏损 >= 1 次：冷却 120 秒
        - 无连续亏损：使用配置的基础冷却时间

        Args:
            task_id (int): 任务ID

        Returns:
            bool: True 表示仍在冷却期内，不可交易；False 表示可以交易
        """
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if not model or not model.last_trade_time:
                return False
            base_cooldown = getattr(model, 'cooldown_seconds', 60) or 60
            consecutive_losses = getattr(model, 'consecutive_losses', 0) or 0
            if consecutive_losses >= 3:
                effective_cooldown = 300
            elif consecutive_losses >= 2:
                effective_cooldown = 180
            elif consecutive_losses >= 1:
                effective_cooldown = 120
            else:
                effective_cooldown = base_cooldown
            elapsed = (china_now_naive() - model.last_trade_time).total_seconds()
            return elapsed < effective_cooldown

    @classmethod
    def can_trade_today(cls, task_id) -> bool:
        """
        检查今日交易次数是否未超限

        若交易日期与上次不同，则重置今日交易计数。

        Args:
            task_id (int): 任务ID

        Returns:
            bool: True 表示今日仍可交易，False 表示已达上限
        """
        today_str = china_now_naive().strftime("%Y%m%d")
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if not model:
                return True
            last_date = getattr(model, 'last_trade_date', None)
            if last_date != today_str:
                model.trade_count_today = 0
                model.last_trade_date = today_str
                model.updated_at = china_now_naive()
                return True
            max_trades = getattr(model, 'max_daily_trades', 50) or 50
            return (model.trade_count_today or 0) < max_trades

    @classmethod
    def update_consecutive_signals(cls, task_id, current_signal: str, required_streak: int = 2):
        """
        更新连续信号计数，用于信号确认机制

        当连续出现相同信号达到指定次数时，确认信号有效。
        若当前信号与上次信号不同，则重置计数。

        Args:
            task_id (int): 任务ID
            current_signal (str): 当前信号(买入/卖出/持有/观望)
            required_streak (int): 确认所需的连续信号次数，默认 2

        Returns:
            bool: True 表示连续信号已达到确认阈值，False 表示未达到
        """
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if not model:
                return False
            last_signal = getattr(model, 'last_signal', None)
            if current_signal in ("买入", "卖出") and current_signal == last_signal:
                model.consecutive_signals = (model.consecutive_signals or 0) + 1
            else:
                model.consecutive_signals = 1 if current_signal in ("买入", "卖出") else 0
            model.last_signal = current_signal
            model.last_check = china_now_naive()
            model.updated_at = china_now_naive()
            return (model.consecutive_signals or 0) >= required_streak

    @classmethod
    def update_peak_and_drawdown(cls, task_id, current_value: float) -> float:
        """
        更新历史峰值并返回当前回撤百分比

        当当前净值超过历史峰值时更新峰值。回撤百分比 = (当前净值 - 峰值) / 峰值 * 100，
        为负数表示从峰值回撤。

        Args:
            task_id (int): 任务ID
            current_value (float): 任务当前净值（可用资金 + 持仓市值）

        Returns:
            float: 回撤百分比（负数，如 -8.5 表示从峰值回撤 8.5%）
        """
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if not model:
                return 0.0
            peak = float(model.peak_value or 0)
            if current_value > peak:
                model.peak_value = current_value
                peak = current_value
            drawdown_pct = 0.0
            if peak > 0:
                drawdown_pct = (current_value - peak) / peak * 100
            model.updated_at = china_now_naive()
            return drawdown_pct

    @classmethod
    def update_consecutive_losses(cls, task_id, is_loss: bool):
        """
        更新连续亏损次数

        若本次为亏损则累加，否则重置为0。连续亏损次数会影响冷却时间。

        Args:
            task_id (int): 任务ID
            is_loss (bool): True 表示本次交易亏损，False 表示盈利或持平

        Returns:
            int: 当前连续亏损次数
        """
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if not model:
                return 0
            if is_loss:
                model.consecutive_losses = (model.consecutive_losses or 0) + 1
            else:
                model.consecutive_losses = 0
            model.updated_at = china_now_naive()
            return model.consecutive_losses

    @classmethod
    def migrate_schema(cls):
        """
        数据库表结构迁移

        检查 auto_trade_tasks 表是否缺少必要字段和索引，
        若缺少则自动添加，支持多次安全运行（幂等操作）。
        具体检查：
        - id 主键列
        - user_id + symbol + strategy 唯一约束
        - 风控相关字段（止损/止盈/回撤/冷却等）
        - enabled 和 user_id 索引
        """
        from .db import engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("auto_trade_tasks")]

        with engine.connect() as conn:
            if "id" not in columns:
                conn.execute(text("ALTER TABLE auto_trade_tasks ADD COLUMN id SERIAL PRIMARY KEY"))

            indexes = inspector.get_indexes("auto_trade_tasks")
            index_names = [idx["name"] for idx in indexes]
            unique_constraints = [c["name"] for c in inspector.get_unique_constraints("auto_trade_tasks")]
            if "uq_user_symbol_strategy" not in index_names and "uq_user_symbol_strategy" not in unique_constraints:
                conn.execute(text(
                    "ALTER TABLE auto_trade_tasks ADD CONSTRAINT uq_user_symbol_strategy "
                    "UNIQUE (user_id, symbol, strategy)"
                ))

            new_cols = {
                "stop_loss_pct": "NUMERIC DEFAULT -5.0",                            # 止损百分比
                "take_profit_pct": "NUMERIC DEFAULT 10.0",                          # 止盈百分比
                "trend_ma_key": "VARCHAR",                                           # 趋势均线周期
                "dynamic_interval": "BOOLEAN DEFAULT FALSE",                        # 是否启用动态间隔
                "last_trade_time": "TIMESTAMP",                                     # 最后交易时间
                "last_trade_direction": "VARCHAR",                                  # 最后交易方向
                "trade_count_today": "INTEGER DEFAULT 0",                           # 今日交易次数
                "last_trade_date": "VARCHAR",                                       # 最后交易日期
                "consecutive_signals": "INTEGER DEFAULT 0",                         # 连续信号计数
                "cooldown_seconds": "INTEGER DEFAULT 60",                           # 冷却时间(秒)
                "max_daily_trades": "INTEGER DEFAULT 50",                           # 每日最大交易次数
                "max_drawdown_pct": "NUMERIC DEFAULT -15.0",                        # 最大回撤阈值
                "peak_value": "NUMERIC DEFAULT 0",                                  # 历史净值峰值
                "consecutive_losses": "INTEGER DEFAULT 0",                          # 连续亏损次数
                "use_multi_factor": "BOOLEAN DEFAULT FALSE",                        # 是否启用多因子评分
                "adaptive_strategy": "BOOLEAN DEFAULT FALSE",                       # 是否启用自适应策略
            }
            for col_name, col_type in new_cols.items():
                if col_name not in columns:
                    conn.execute(text(f"ALTER TABLE auto_trade_tasks ADD COLUMN {col_name} {col_type}"))

            idx_names = [idx["name"] for idx in inspector.get_indexes("auto_trade_tasks")]
            if "ix_auto_trade_tasks_enabled" not in idx_names:
                conn.execute(text("CREATE INDEX ix_auto_trade_tasks_enabled ON auto_trade_tasks (enabled)"))
            if "ix_auto_trade_tasks_user_id" not in idx_names:
                conn.execute(text("CREATE INDEX ix_auto_trade_tasks_user_id ON auto_trade_tasks (user_id)"))

            conn.commit()
