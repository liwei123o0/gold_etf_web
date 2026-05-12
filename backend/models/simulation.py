"""
模拟交易数据模型

定义模拟交易系统中的账户、持仓和订单的 ORM 模型及业务操作类，
支持模拟账户的创建、持仓管理和交易记录等功能。
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import Base, get_session
from ..utils.timezone import china_now_naive
import logging

logger = logging.getLogger(__name__)

class SimAccount(Base):
    """
    模拟交易账户 ORM 模型

    对应数据库表 sim_accounts，存储用户的模拟交易账户信息，
    包括初始资金、可用资金、冻结资金和已实现盈亏等。
    """
    __tablename__ = "sim_accounts"

    user_id = Column(Integer, primary_key=True)                                    # 用户ID，主键
    initial_capital = Column(Numeric, nullable=False)                              # 初始资金
    cash = Column(Numeric, nullable=False, default=0)                              # 可用资金
    frozen_cash = Column(Numeric, nullable=False, default=0)                       # 冻结资金
    realized_pnl = Column(Numeric, nullable=False, default=0)                      # 已实现盈亏
    created_at = Column(DateTime, default=china_now_naive)                         # 创建时间
    updated_at = Column(DateTime, default=china_now_naive, onupdate=china_now_naive)  # 更新时间


class SimPosition(Base):
    """
    模拟持仓 ORM 模型

    对应数据库表 sim_positions，存储用户的模拟持仓信息，
    包括股票代码、持仓数量、平均成本、当前价格和策略类型等。
    唯一约束：(user_id, symbol, strategy_type)，同一用户同一股票同一策略只能有一条持仓记录。
    """
    __tablename__ = "sim_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "strategy_type", name="uq_user_symbol_strategy"),
    )

    id = Column(Integer, primary_key=True)                                         # 持仓记录ID，主键
    user_id = Column(Integer, nullable=False)                                      # 用户ID
    symbol = Column(String, nullable=False)                                        # 股票代码
    name = Column(String, nullable=False)                                          # 股票名称
    shares = Column(Integer, nullable=False, default=0)                            # 持仓数量（股）
    avg_cost = Column(Numeric, nullable=False, default=0)                          # 平均成本价
    current_price = Column(Numeric, nullable=False, default=0)                     # 当前价格
    strategy_type = Column(String, nullable=False, default="manual")               # 策略类型(manual手动/grid网格/ma_trend均线趋势)
    unrealized_pnl = Column(Numeric, nullable=False, default=0)                    # 浮动盈亏金额
    unrealized_pnl_pct = Column(Numeric, nullable=False, default=0)                # 浮动盈亏百分比(%)


class SimOrder(Base):
    """
    模拟订单 ORM 模型

    对应数据库表 sim_orders，存储用户的模拟交易订单记录，
    包括交易方向、股票信息、成交价格、手续费和盈亏等。
    """
    __tablename__ = "sim_orders"

    id = Column(String, primary_key=True)                                          # 订单ID，主键
    user_id = Column(Integer, nullable=False)                                      # 用户ID
    direction = Column(String, nullable=False)                                     # 交易方向(买入/卖出)
    symbol = Column(String, nullable=False)                                        # 股票代码
    name = Column(String, nullable=False)                                          # 股票名称
    price = Column(Numeric, nullable=False)                                        # 成交价格
    shares = Column(Integer, nullable=False)                                       # 成交数量（股）
    commission = Column(Numeric, nullable=False)                                   # 手续费
    pnl = Column(Numeric, nullable=False, default=0)                               # 盈亏金额
    trade_type = Column(String, nullable=False, default="manual")                  # 交易类型(manual手动/auto自动)
    timestamp = Column(DateTime, nullable=False)                                   # 成交时间


class SimulationAccount:
    """
    模拟账户业务操作类

    提供模拟账户的查询、新增/更新（upsert）和删除等操作，
    将 ORM 行数据转换为前端可用的字典格式。
    """

    @classmethod
    def from_row(cls, row):
        """
        将 ORM 行对象转换为字典格式

        Args:
            row: SimAccount ORM 行对象，若为 None 则返回 None

        Returns:
            dict | None: 包含账户信息的字典，包括初始资金、可用资金、冻结资金、
                         市值、总资产、未实现盈亏、已实现盈亏和总盈亏；
                         若 row 为 None 则返回 None
        """
        if row is None:
            return None
        return {
            "initial_capital": float(row.initial_capital),                         # 初始资金
            "cash": float(row.cash),                                               # 可用资金
            "frozen_cash": float(row.frozen_cash),                                 # 冻结资金
            "market_value": 0.0,                                                   # 持仓市值（需外部计算补充）
            "total_assets": float(row.cash),                                       # 总资产（需外部计算补充）
            "unrealized_pnl": 0.0,                                                # 未实现盈亏（需外部计算补充）
            "realized_pnl": float(row.realized_pnl),                               # 已实现盈亏
            "total_pnl": 0.0,                                                     # 总盈亏（需外部计算补充）
        }

    @classmethod
    def find_by_user_id(cls, user_id):
        """
        根据用户ID查询模拟账户信息

        Args:
            user_id (int): 用户ID

        Returns:
            dict | None: 账户信息字典，若用户不存在则返回 None
        """
        with get_session() as session:
            row = session.query(SimAccount).filter(SimAccount.user_id == user_id).first()
            return cls.from_row(row)

    @classmethod
    def upsert(cls, user_id, initial_capital, cash, frozen_cash=0.0, realized_pnl=0.0):
        """
        新增或更新模拟账户信息

        若该用户ID的账户已存在则更新，否则新增。使用 PostgreSQL 的
        ON CONFLICT DO UPDATE 语法实现原子性 upsert 操作。

        Args:
            user_id (int): 用户ID
            initial_capital (float): 初始资金
            cash (float): 可用资金
            frozen_cash (float): 冻结资金，默认 0.0
            realized_pnl (float): 已实现盈亏，默认 0.0
        """
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
        """
        根据用户ID删除模拟账户

        Args:
            user_id (int): 用户ID
        """
        with get_session() as session:
            session.query(SimAccount).filter(SimAccount.user_id == user_id).delete()


class SimulationPosition:
    """
    模拟持仓业务操作类

    提供模拟持仓的查询、新增/更新（upsert）和删除等操作，
    自动计算未实现盈亏、盈亏百分比和持仓市值。
    """

    @classmethod
    def from_row(cls, row):
        """
        将 ORM 行对象转换为字典格式

        优先从数据库读取已持久化的浮动盈亏数据，
        若数据库值为0则兜底重新计算。

        Args:
            row: SimPosition ORM 行对象，若为 None 则返回 None

        Returns:
            dict | None: 包含持仓信息的字典
        """
        if row is None:
            return None
        shares = row.shares
        avg_cost = float(row.avg_cost)
        current_price = float(row.current_price)
        market_value = shares * current_price

        unrealized = (current_price - avg_cost) * shares if shares > 0 else 0
        unrealized_pct = ((current_price - avg_cost) / avg_cost * 100) if (shares > 0 and avg_cost > 0) else 0

        return {
            "symbol": row.symbol,
            "name": row.name,
            "shares": shares,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "unrealized_pnl": round(unrealized, 2),
            "unrealized_pnl_pct": round(unrealized_pct, 2),
            "strategy_type": getattr(row, 'strategy_type', 'manual') or 'manual',
        }

    @classmethod
    def find_by_user_id(cls, user_id, strategy=None):
        """
        根据用户ID查询所有有效持仓（持仓数量大于0）

        Args:
            user_id (int): 用户ID
            strategy (str | None): 策略类型过滤，若指定则只返回该策略的持仓

        Returns:
            list[dict]: 持仓信息字典列表
        """
        with get_session() as session:
            query = session.query(SimPosition).filter(
                SimPosition.user_id == user_id, SimPosition.shares > 0
            )
            if strategy:
                query = query.filter(SimPosition.strategy_type == strategy)
            rows = query.all()
            return [cls.from_row(r) for r in rows]

    @classmethod
    def find_by_strategy(cls, user_id, symbol, strategy):
        """
        根据用户ID、股票代码和策略类型查询持仓

        Args:
            user_id (int): 用户ID
            symbol (str): 股票代码
            strategy (str): 策略类型

        Returns:
            dict | None: 持仓信息字典，若不存在则返回 None
        """
        with get_session() as session:
            row = session.query(SimPosition).filter(
                SimPosition.user_id == user_id,
                SimPosition.symbol == symbol,
                SimPosition.strategy_type == strategy,
            ).first()
            return cls.from_row(row)

    @classmethod
    def upsert(cls, user_id, symbol, name, shares, avg_cost, current_price, strategy_type="manual"):
        """
        新增或更新模拟持仓

        若持仓数量 <= 0，则删除该持仓记录；否则使用 PostgreSQL 的
        ON CONFLICT DO UPDATE 语法实现原子性 upsert 操作。
        自动计算并持久化浮动盈亏和盈亏百分比。

        Args:
            user_id (int): 用户ID
            symbol (str): 股票代码
            name (str): 股票名称
            shares (int): 持仓数量
            avg_cost (float): 平均成本价
            current_price (float): 当前价格
            strategy_type (str): 策略类型，默认 "manual"
        """
        if shares > 0 and avg_cost > 0:
            unrealized_pnl = round((current_price - avg_cost) * shares, 2)
            unrealized_pnl_pct = round((current_price - avg_cost) / avg_cost * 100, 2) if avg_cost > 0 else 0
        else:
            unrealized_pnl = 0
            unrealized_pnl_pct = 0

        with get_session() as session:
            if shares <= 0:
                session.query(SimPosition).filter(
                    SimPosition.user_id == user_id,
                    SimPosition.symbol == symbol,
                    SimPosition.strategy_type == strategy_type,
                ).delete()
            else:
                stmt = pg_insert(SimPosition).values(
                    user_id=user_id,
                    symbol=symbol,
                    name=name,
                    shares=shares,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    strategy_type=strategy_type,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["user_id", "symbol", "strategy_type"],
                    set_={
                        "name": stmt.excluded.name,
                        "shares": stmt.excluded.shares,
                        "avg_cost": stmt.excluded.avg_cost,
                        "current_price": stmt.excluded.current_price,
                        "strategy_type": stmt.excluded.strategy_type,
                        "unrealized_pnl": stmt.excluded.unrealized_pnl,
                        "unrealized_pnl_pct": stmt.excluded.unrealized_pnl_pct,
                    },
                )
                session.execute(stmt)

    @classmethod
    def delete_by_user_id(cls, user_id):
        """
        根据用户ID删除所有持仓记录

        Args:
            user_id (int): 用户ID
        """
        with get_session() as session:
            session.query(SimPosition).filter(SimPosition.user_id == user_id).delete()


class SimulationOrder:
    """
    模拟订单业务操作类

    提供模拟订单的查询、插入和删除等操作，
    将 ORM 行数据转换为前端可用的字典格式。
    """

    @classmethod
    def from_row(cls, row):
        """
        将 ORM 行对象转换为字典格式

        Args:
            row: SimOrder ORM 行对象，若为 None 则返回 None

        Returns:
            dict | None: 包含订单信息的字典，包括订单ID、方向、股票信息、
                         成交价格、数量、手续费、成交时间、盈亏和交易类型；
                         若 row 为 None 则返回 None
        """
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
            "trade_type": row.trade_type or "manual",
        }

    @classmethod
    def find_by_user_id(cls, user_id, limit=50):
        """
        根据用户ID查询订单记录，按时间倒序排列

        Args:
            user_id (int): 用户ID
            limit (int): 返回记录数量上限，默认 50

        Returns:
            list[dict]: 订单信息字典列表，按成交时间倒序排列
        """
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
        """
        插入一条新的模拟订单记录

        Args:
            order_id (str): 订单ID
            user_id (int): 用户ID
            direction (str): 交易方向(买入/卖出)
            symbol (str): 股票代码
            name (str): 股票名称
            price (float): 成交价格
            shares (int): 成交数量
            commission (float): 手续费
            pnl (float): 盈亏金额，默认 0
            trade_type (str): 交易类型(manual手动/auto自动)，默认 "manual"
        """
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
        """
        根据用户ID删除所有订单记录

        Args:
            user_id (int): 用户ID
        """
        with get_session() as session:
            session.query(SimOrder).filter(SimOrder.user_id == user_id).delete()

    @classmethod
    def migrate_schema(cls):
        """
        数据库表结构迁移

        检查 sim_positions 和 sim_orders 表是否缺少必要字段，
        若缺少则自动添加，支持多次安全运行（幂等操作）。
        具体检查：
        - sim_positions 表的 strategy_type、unrealized_pnl、unrealized_pnl_pct 字段
        - sim_orders 表的 trade_type 字段
        - sim_positions 表的唯一约束 (user_id, symbol, strategy_type)
        """
        from .db import engine
        from sqlalchemy import inspect, text
        inspector = inspect(engine)

        with engine.begin() as conn:
            for table_name in ["sim_positions", "sim_orders"]:
                columns = [c["name"] for c in inspector.get_columns(table_name)]
                if table_name == "sim_positions":
                    if "strategy_type" not in columns:
                        conn.execute(text("ALTER TABLE sim_positions ADD COLUMN strategy_type VARCHAR DEFAULT 'manual'"))
                    if "unrealized_pnl" not in columns:
                        conn.execute(text("ALTER TABLE sim_positions ADD COLUMN unrealized_pnl NUMERIC DEFAULT 0"))
                    if "unrealized_pnl_pct" not in columns:
                        conn.execute(text("ALTER TABLE sim_positions ADD COLUMN unrealized_pnl_pct NUMERIC DEFAULT 0"))

                    constraints = inspector.get_unique_constraints(table_name)
                    constraint_names = [c["name"] for c in constraints if c.get("name")]

                    for constraint in constraints:
                        cols = set(constraint.get("column_names", []))
                        if cols == {"user_id", "symbol"} and "strategy_type" not in cols:
                            constraint_name = constraint.get("name")
                            if constraint_name:
                                conn.execute(text(f"ALTER TABLE sim_positions DROP CONSTRAINT {constraint_name}"))
                                logger.info(f"[Migration] 删除旧唯一约束: {constraint_name}")

                    new_constraint_exists = any(
                        set(c.get("column_names", [])) == {"user_id", "symbol", "strategy_type"}
                        for c in constraints
                    )
                    if not new_constraint_exists:
                        try:
                            conn.execute(text(
                                "ALTER TABLE sim_positions "
                                "ADD CONSTRAINT uq_user_symbol_strategy "
                                "UNIQUE (user_id, symbol, strategy_type)"
                            ))
                            logger.info("[Migration] 创建新唯一约束: uq_user_symbol_strategy")
                        except Exception as e:
                            if "already exists" in str(e):
                                logger.info("[Migration] 唯一约束 uq_user_symbol_strategy 已存在，跳过创建")
                            else:
                                raise

                if table_name == "sim_orders" and "trade_type" not in columns:
                    conn.execute(text("ALTER TABLE sim_orders ADD COLUMN trade_type VARCHAR DEFAULT 'manual'"))
