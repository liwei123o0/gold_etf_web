"""Auto Trade Task Model - SQLAlchemy ORM persistence"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, func, text, UniqueConstraint

from .db import Base, get_session
from ..utils.timezone import china_now_naive


class AutoTradeTaskModel(Base):
    __tablename__ = "auto_trade_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "strategy", name="uq_user_symbol_strategy"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    symbol = Column(String, nullable=False)
    strategy = Column(String, nullable=False, default="grid")
    grid_count = Column(Integer, default=10)  # 网格数量
    grid_spread = Column(Numeric, default=0.10)  # 网格间距(百分比)
    base_ma_key = Column(String, default="MA20")  # 基础均线周期(MA5/MA10/MA20等)
    macd_ma_key = Column(String, nullable=True)  # MACD均线周期
    position_size = Column(Numeric, default=1.0)  # 仓位大小(0.0-1.0)
    check_interval = Column(Integer, default=30)  # 检查间隔(秒)
    allocated_funds = Column(Numeric, default=0)  # 分配资金总额
    enabled = Column(Boolean, nullable=False, default=False)  # 是否启用
    last_check = Column(DateTime, nullable=True)  # 最后检查时间
    last_signal = Column(String, nullable=True)  # 最后信号
    task_cash = Column(Numeric, default=0)  # 任务可用资金
    task_pnl = Column(Numeric, default=0)  # 任务累计盈亏
    position_shares = Column(Integer, default=0)  # 持仓数量
    position_avg_cost = Column(Numeric, default=0)  # 持仓平均成本
    task_name = Column(String, default="")  # 任务名称
    unrealized_pnl = Column(Numeric, default=0)  # 浮动盈亏
    stop_loss_pct = Column(Numeric, default=-5.0)  # 止损百分比
    take_profit_pct = Column(Numeric, default=10.0)  # 止盈百分比
    trend_ma_key = Column(String, nullable=True)  # 趋势均线周期
    dynamic_interval = Column(Boolean, default=False)  # 是否启用动态间隔
    last_trade_time = Column(DateTime, nullable=True)  # 最后交易时间
    last_trade_direction = Column(String, nullable=True)  # 最后交易方向(买入/卖出)
    trade_count_today = Column(Integer, default=0)  # 今日交易次数
    last_trade_date = Column(String, nullable=True)  # 最后交易日期
    consecutive_signals = Column(Integer, default=0)  # 连续信号计数
    cooldown_seconds = Column(Integer, default=60)  # 冷却时间(秒)
    max_daily_trades = Column(Integer, default=50)  # 每日最大交易次数
    max_drawdown_pct = Column(Numeric, default=-15.0)  # 最大回撤阈值(%)
    peak_value = Column(Numeric, default=0)  # 历史净值峰值(用于回撤计算)
    consecutive_losses = Column(Integer, default=0)  # 连续亏损次数
    created_at = Column(DateTime, default=china_now_naive)  # 创建时间
    updated_at = Column(DateTime, default=china_now_naive, onupdate=china_now_naive)  # 更新时间


class AutoTradeTask:
    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return {
            "id": row.id,
            "user_id": row.user_id,
            "symbol": row.symbol,
            "strategy": row.strategy,
            "grid_count": row.grid_count,
            "grid_spread": float(row.grid_spread),
            "base_ma_key": row.base_ma_key,
            "macd_ma_key": row.macd_ma_key,
            "position_size": float(row.position_size),
            "check_interval": row.check_interval,
            "allocated_funds": float(row.allocated_funds or 0),
            "enabled": bool(row.enabled),
            "last_check": row.last_check,
            "last_signal": row.last_signal,
            "task_cash": float(row.task_cash or 0),
            "task_pnl": float(row.task_pnl or 0),
            "position_shares": row.position_shares or 0,
            "position_avg_cost": float(row.position_avg_cost or 0),
            "task_name": row.task_name or row.symbol,
            "unrealized_pnl": float(row.unrealized_pnl or 0),
            "stop_loss_pct": float(getattr(row, 'stop_loss_pct', -5.0) or -5.0),
            "take_profit_pct": float(getattr(row, 'take_profit_pct', 10.0) or 10.0),
            "trend_ma_key": getattr(row, 'trend_ma_key', None),
            "dynamic_interval": bool(getattr(row, 'dynamic_interval', False)),
            "last_trade_time": getattr(row, 'last_trade_time', None),
            "last_trade_direction": getattr(row, 'last_trade_direction', None),
            "trade_count_today": getattr(row, 'trade_count_today', 0) or 0,
            "last_trade_date": getattr(row, 'last_trade_date', None),
            "consecutive_signals": getattr(row, 'consecutive_signals', 0) or 0,
            "cooldown_seconds": getattr(row, 'cooldown_seconds', 60) or 60,
            "max_daily_trades": getattr(row, 'max_daily_trades', 50) or 50,
            "max_drawdown_pct": float(getattr(row, 'max_drawdown_pct', -15.0) or -15.0),
            "peak_value": float(getattr(row, 'peak_value', 0) or 0),
            "consecutive_losses": getattr(row, 'consecutive_losses', 0) or 0,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    def find_by_user(cls, user_id):
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
                    created_at=china_now_naive(),
                    updated_at=china_now_naive(),
                )
                session.add(model)
                session.flush()
                return model.id

    @classmethod
    def update_enabled(cls, task_id, enabled: bool):
        with get_session() as session:
            existing = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            if existing:
                existing.enabled = enabled
                existing.updated_at = china_now_naive()

    @classmethod
    def find_by_id(cls, task_id):
        with get_session() as session:
            row = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).first()
            return cls.from_row(row) if row else None

    @classmethod
    def update_last_check(cls, task_id, last_signal: str = None):
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
    def update_runtime(cls, user_id, symbol, task_cash: float, task_pnl: float,
                       position_shares: int, position_avg_cost: float,
                       unrealized_pnl: float = 0, task_name: str = None):
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
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
        with get_session() as session:
            result = session.query(func.coalesce(func.sum(AutoTradeTaskModel.allocated_funds), 0)).filter(
                AutoTradeTaskModel.user_id == user_id
            ).scalar()
            return float(result)

    @classmethod
    def delete_task(cls, task_id):
        with get_session() as session:
            session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.id == task_id,
            ).delete()

    @classmethod
    def delete_task_by_symbol(cls, user_id, symbol):
        with get_session() as session:
            session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
            ).delete()

    @classmethod
    def record_trade(cls, user_id, symbol, direction: str):
        """记录一次交易：更新最后交易时间、方向、今日计数"""
        today_str = china_now_naive().strftime("%Y%m%d")
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
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
    def can_trade_today(cls, user_id, symbol) -> bool:
        """检查今日交易次数是否未超限"""
        today_str = china_now_naive().strftime("%Y%m%d")
        with get_session() as session:
            model = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
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
        """更新历史峰值并返回当前回撤百分比。
        current_value = 任务当前净值 (可用资金 + 持仓市值)
        返回: drawdown_pct (负数，如 -8.5 表示从峰值回撤 8.5%)
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
        """更新连续亏损次数，返回当前连续亏损数"""
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
        """Add new columns for existing tables (safe to run multiple times)"""
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
                "stop_loss_pct": "NUMERIC DEFAULT -5.0",
                "take_profit_pct": "NUMERIC DEFAULT 10.0",
                "trend_ma_key": "VARCHAR",
                "dynamic_interval": "BOOLEAN DEFAULT FALSE",
                "last_trade_time": "TIMESTAMP",
                "last_trade_direction": "VARCHAR",
                "trade_count_today": "INTEGER DEFAULT 0",
                "last_trade_date": "VARCHAR",
                "consecutive_signals": "INTEGER DEFAULT 0",
                "cooldown_seconds": "INTEGER DEFAULT 60",
                "max_daily_trades": "INTEGER DEFAULT 50",
                "max_drawdown_pct": "NUMERIC DEFAULT -15.0",
                "peak_value": "NUMERIC DEFAULT 0",
                "consecutive_losses": "INTEGER DEFAULT 0",
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
