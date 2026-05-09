"""Sim Trading Models - SQLAlchemy ORM persistence"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import Base, get_session
from ..utils.timezone import china_now_naive


class SimAccount(Base):
    __tablename__ = "sim_accounts"

    user_id = Column(Integer, primary_key=True)  # 用户ID
    initial_capital = Column(Numeric, nullable=False)  # 初始资金
    cash = Column(Numeric, nullable=False, default=0)  # 可用资金
    frozen_cash = Column(Numeric, nullable=False, default=0)  # 冻结资金
    realized_pnl = Column(Numeric, nullable=False, default=0)  # 已实现盈亏
    created_at = Column(DateTime, default=china_now_naive)  # 创建时间
    updated_at = Column(DateTime, default=china_now_naive, onupdate=china_now_naive)  # 更新时间


class SimPosition(Base):
    __tablename__ = "sim_positions"

    id = Column(Integer, primary_key=True)  # 持仓ID
    user_id = Column(Integer, nullable=False)  # 用户ID
    symbol = Column(String, nullable=False)  # 股票代码
    name = Column(String, nullable=False)  # 股票名称
    shares = Column(Integer, nullable=False, default=0)  # 持仓数量
    avg_cost = Column(Numeric, nullable=False, default=0)  # 平均成本
    current_price = Column(Numeric, nullable=False, default=0)  # 当前价格


class SimOrder(Base):
    __tablename__ = "sim_orders"

    id = Column(String, primary_key=True)  # 订单ID
    user_id = Column(Integer, nullable=False)  # 用户ID
    direction = Column(String, nullable=False)  # 交易方向(买入/卖出)
    symbol = Column(String, nullable=False)  # 股票代码
    name = Column(String, nullable=False)  # 股票名称
    price = Column(Numeric, nullable=False)  # 成交价格
    shares = Column(Integer, nullable=False)  # 成交数量
    commission = Column(Numeric, nullable=False)  # 手续费
    pnl = Column(Numeric, nullable=False, default=0)  # 盈亏
    trade_type = Column(String, nullable=False, default="manual")  # 交易类型(manual手动/auto自动)
    timestamp = Column(DateTime, nullable=False)  # 成交时间


class SimulationAccount:
    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return {
            "initial_capital": float(row.initial_capital),
            "cash": float(row.cash),
            "frozen_cash": float(row.frozen_cash),
            "market_value": 0.0,
            "total_assets": float(row.cash),
            "unrealized_pnl": 0.0,
            "realized_pnl": float(row.realized_pnl),
            "total_pnl": 0.0,
        }

    @classmethod
    def find_by_user_id(cls, user_id):
        with get_session() as session:
            row = session.query(SimAccount).filter(SimAccount.user_id == user_id).first()
            return cls.from_row(row)

    @classmethod
    def upsert(cls, user_id, initial_capital, cash, frozen_cash=0.0, realized_pnl=0.0):
        with get_session() as session:
            stmt = pg_insert(SimAccount).values(
                user_id=user_id,
                initial_capital=initial_capital,
                cash=cash,
                frozen_cash=frozen_cash,
                realized_pnl=realized_pnl,
                updated_at=china_now_naive(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "initial_capital": stmt.excluded.initial_capital,
                    "cash": stmt.excluded.cash,
                    "frozen_cash": stmt.excluded.frozen_cash,
                    "realized_pnl": stmt.excluded.realized_pnl,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)

    @classmethod
    def delete_by_user_id(cls, user_id):
        with get_session() as session:
            session.query(SimAccount).filter(SimAccount.user_id == user_id).delete()


class SimulationPosition:
    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        unrealized = (float(row.current_price) - float(row.avg_cost)) * row.shares
        unrealized_pct = (
            (float(row.current_price) - float(row.avg_cost)) / float(row.avg_cost) * 100
            if float(row.avg_cost) else 0
        )
        return {
            "symbol": row.symbol,
            "name": row.name,
            "shares": row.shares,
            "avg_cost": float(row.avg_cost),
            "current_price": float(row.current_price),
            "unrealized_pnl": unrealized,
            "unrealized_pnl_pct": unrealized_pct,
        }

    @classmethod
    def find_by_user_id(cls, user_id):
        with get_session() as session:
            rows = session.query(SimPosition).filter(
                SimPosition.user_id == user_id, SimPosition.shares > 0
            ).all()
            return [cls.from_row(r) for r in rows]

    @classmethod
    def upsert(cls, user_id, symbol, name, shares, avg_cost, current_price):
        with get_session() as session:
            if shares <= 0:
                session.query(SimPosition).filter(
                    SimPosition.user_id == user_id, SimPosition.symbol == symbol
                ).delete()
            else:
                stmt = pg_insert(SimPosition).values(
                    user_id=user_id,
                    symbol=symbol,
                    name=name,
                    shares=shares,
                    avg_cost=avg_cost,
                    current_price=current_price,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["user_id", "symbol"],
                    set_={
                        "name": stmt.excluded.name,
                        "shares": stmt.excluded.shares,
                        "avg_cost": stmt.excluded.avg_cost,
                        "current_price": stmt.excluded.current_price,
                    },
                )
                session.execute(stmt)

    @classmethod
    def delete_by_user_id(cls, user_id):
        with get_session() as session:
            session.query(SimPosition).filter(SimPosition.user_id == user_id).delete()


class SimulationOrder:
    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return {
            "id": row.id,
            "direction": row.direction,
            "symbol": row.symbol,
            "name": row.name,
            "price": float(row.price),
            "shares": row.shares,
            "commission": float(row.commission),
            "timestamp": row.timestamp.strftime("%Y-%m-%d %H:%M:%S") if row.timestamp else "",
            "pnl": float(row.pnl),
            "trade_type": row.trade_type,
        }

    @classmethod
    def find_by_user_id(cls, user_id, limit=50):
        with get_session() as session:
            rows = (
                session.query(SimOrder)
                .filter(SimOrder.user_id == user_id)
                .order_by(SimOrder.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [cls.from_row(r) for r in rows]

    @classmethod
    def insert(cls, order_id, user_id, direction, symbol, name, price, shares, commission, pnl=0, trade_type="manual"):
        with get_session() as session:
            order = SimOrder(
                id=order_id,
                user_id=user_id,
                direction=direction,
                symbol=symbol,
                name=name,
                price=price,
                shares=shares,
                commission=commission,
                pnl=pnl,
                trade_type=trade_type,
                timestamp=china_now_naive(),
            )
            session.add(order)

    @classmethod
    def delete_by_user_id(cls, user_id):
        with get_session() as session:
            session.query(SimOrder).filter(SimOrder.user_id == user_id).delete()
