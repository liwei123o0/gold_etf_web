"""Auto Trade Task Model - SQLAlchemy ORM persistence"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, func

from .db import Base, get_session


class AutoTradeTaskModel(Base):
    __tablename__ = "auto_trade_tasks"

    user_id = Column(Integer, primary_key=True)
    symbol = Column(String, primary_key=True)
    strategy = Column(String, nullable=False, default="grid")
    grid_count = Column(Integer, default=10)
    grid_spread = Column(Numeric, default=0.10)
    base_ma_key = Column(String, default="MA20")
    macd_ma_key = Column(String, nullable=True)
    position_size = Column(Numeric, default=1.0)
    check_interval = Column(Integer, default=30)
    allocated_funds = Column(Numeric, default=0)
    enabled = Column(Boolean, nullable=False, default=False)
    last_check = Column(DateTime, nullable=True)
    last_signal = Column(String, nullable=True)
    task_cash = Column(Numeric, default=0)
    task_pnl = Column(Numeric, default=0)
    position_shares = Column(Integer, default=0)
    position_avg_cost = Column(Numeric, default=0)
    task_name = Column(String, default="")
    unrealized_pnl = Column(Numeric, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutoTradeTask:
    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return {
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
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    def find_by_user(cls, user_id):
        with get_session() as session:
            rows = (
                session.query(AutoTradeTaskModel)
                .filter(AutoTradeTaskModel.user_id == user_id)
                .order_by(AutoTradeTaskModel.symbol)
                .all()
            )
            return [cls.from_row(r) for r in rows]

    @classmethod
    def find_by_symbol(cls, user_id, symbol):
        with get_session() as session:
            row = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
            ).first()
            return cls.from_row(row) if row else None

    @classmethod
    def find_all_enabled(cls):
        with get_session() as session:
            rows = (
                session.query(AutoTradeTaskModel)
                .filter(AutoTradeTaskModel.enabled == True)
                .order_by(AutoTradeTaskModel.user_id, AutoTradeTaskModel.symbol)
                .all()
            )
            return [cls.from_row(r) for r in rows]

    @classmethod
    def upsert(cls, user_id, symbol, config: dict):
        with get_session() as session:
            existing = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
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
                existing.task_cash = config.get("task_cash", existing.task_cash)
                existing.task_pnl = config.get("task_pnl", existing.task_pnl)
                existing.position_shares = config.get("position_shares", existing.position_shares)
                existing.position_avg_cost = config.get("position_avg_cost", existing.position_avg_cost)
                existing.unrealized_pnl = config.get("unrealized_pnl", existing.unrealized_pnl)
                existing.task_name = config.get("task_name", existing.task_name)
                existing.updated_at = datetime.utcnow()
            else:
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
                    allocated_funds=config.get("allocated_funds", 0),
                    enabled=config.get("enabled", False),
                    last_check=config.get("last_check"),
                    last_signal=config.get("last_signal"),
                    task_cash=config.get("task_cash", config.get("allocated_funds", 0)),
                    task_pnl=config.get("task_pnl", 0),
                    position_shares=config.get("position_shares", 0),
                    position_avg_cost=config.get("position_avg_cost", 0),
                    unrealized_pnl=config.get("unrealized_pnl", 0),
                    task_name=config.get("task_name", symbol),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(model)

    @classmethod
    def update_enabled(cls, user_id, symbol, enabled: bool):
        with get_session() as session:
            existing = session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
            ).first()
            if existing:
                existing.enabled = enabled
                existing.updated_at = datetime.utcnow()
            else:
                model = AutoTradeTaskModel(
                    user_id=user_id,
                    symbol=symbol,
                    enabled=enabled,
                )
                session.add(model)

    @classmethod
    def update_last_check(cls, user_id, symbol, last_check=None, last_signal: str = None):
        from datetime import datetime as dt
        with get_session() as session:
            session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
            ).update({
                AutoTradeTaskModel.last_check: dt.utcnow(),
                AutoTradeTaskModel.last_signal: last_signal,
                AutoTradeTaskModel.updated_at: dt.utcnow(),
            })

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
                model.updated_at = datetime.utcnow()
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
    def delete_task(cls, user_id, symbol):
        with get_session() as session:
            session.query(AutoTradeTaskModel).filter(
                AutoTradeTaskModel.user_id == user_id,
                AutoTradeTaskModel.symbol == symbol,
            ).delete()
