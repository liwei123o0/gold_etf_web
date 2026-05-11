"""
模拟交易系统设置数据模型

定义模拟交易系统的全局费率设置和按标的费率设置的 ORM 模型及业务操作类，
支持佣金、印花税、过户费等费率参数的配置管理。
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import Base, get_session
from ..utils.timezone import china_now_naive


class SimSetting(Base):
    """
    模拟交易全局设置 ORM 模型

    对应数据库表 sim_settings，存储模拟交易的全局费率设置，
    包括佣金费率、最低佣金、印花税率和过户费率。
    通常只有一条记录（id=1）。
    """
    __tablename__ = "sim_settings"

    id = Column(Integer, primary_key=True)                                         # 设置ID，主键
    commission_rate = Column(Numeric, nullable=False, default=0.0003)              # 佣金费率（万分之三）
    min_commission = Column(Numeric, nullable=False, default=5.0)                  # 最低佣金（元）
    stamp_tax_rate = Column(Numeric, nullable=False, default=0.001)                # 印花税率（千分之一，仅卖出收取）
    transfer_fee_rate = Column(Numeric, nullable=False, default=0.00002)           # 过户费率（十万分之二）
    updated_at = Column(DateTime, default=china_now_naive, onupdate=china_now_naive)  # 更新时间


class SimSymbolSetting(Base):
    """
    模拟交易按标的费率设置 ORM 模型

    对应数据库表 sim_symbol_settings，存储特定股票代码的费率覆盖设置。
    字段为可空，若某字段为 None 则使用全局默认值。
    """
    __tablename__ = "sim_symbol_settings"

    symbol = Column(String, primary_key=True)                                      # 股票代码，主键
    commission_rate = Column(Numeric, nullable=True)                               # 佣金费率，None 时使用全局值
    min_commission = Column(Numeric, nullable=True)                                # 最低佣金，None 时使用全局值
    stamp_tax_rate = Column(Numeric, nullable=True)                                # 印花税率，None 时使用全局值
    transfer_fee_rate = Column(Numeric, nullable=True)                             # 过户费率，None 时使用全局值
    updated_at = Column(DateTime, default=china_now_naive, onupdate=china_now_naive)  # 更新时间


class SimSettings:
    """
    模拟交易设置业务操作类

    提供全局费率设置和按标的费率设置的查询、更新和管理功能，
    支持按标的覆盖全局默认费率。
    """

    @staticmethod
    def _get_defaults():
        """
        获取默认费率配置

        Returns:
            dict: 默认费率字典，包含：
                - commission_rate (float): 佣金费率，默认 0.0003
                - min_commission (float): 最低佣金，默认 5.0
                - stamp_tax_rate (float): 印花税率，默认 0.001
                - transfer_fee_rate (float): 过户费率，默认 0.00002
        """
        return {
            "commission_rate": 0.0003,
            "min_commission": 5.0,
            "stamp_tax_rate": 0.001,
            "transfer_fee_rate": 0.00002,
        }

    @staticmethod
    def get(symbol=None):
        """
        获取费率设置

        查询优先级：按标的设置 > 全局设置 > 默认值。
        若指定了 symbol 且该标的有专属设置，则用专属设置覆盖默认值中非空的字段；
        否则返回全局设置或默认值。

        Args:
            symbol (str | None): 股票代码，若指定则查询该标的的费率设置，默认 None

        Returns:
            dict: 费率设置字典，包含 commission_rate、min_commission、stamp_tax_rate、transfer_fee_rate
        """
        defaults = SimSettings._get_defaults()

        with get_session() as session:
            if symbol:
                row = session.query(SimSymbolSetting).filter(
                    SimSymbolSetting.symbol == symbol
                ).first()
                if row:
                    result = defaults.copy()
                    if row.commission_rate is not None:
                        result["commission_rate"] = float(row.commission_rate)
                    if row.min_commission is not None:
                        result["min_commission"] = float(row.min_commission)
                    if row.stamp_tax_rate is not None:
                        result["stamp_tax_rate"] = float(row.stamp_tax_rate)
                    if row.transfer_fee_rate is not None:
                        result["transfer_fee_rate"] = float(row.transfer_fee_rate)
                    return result

            row = session.query(SimSetting).filter(SimSetting.id == 1).first()
            if row:
                return {
                    "commission_rate": float(row.commission_rate),
                    "min_commission": float(row.min_commission),
                    "stamp_tax_rate": float(row.stamp_tax_rate),
                    "transfer_fee_rate": float(row.transfer_fee_rate),
                }

        return defaults

    @staticmethod
    def update(commission_rate, min_commission, stamp_tax_rate, transfer_fee_rate):
        """
        更新全局费率设置

        使用 PostgreSQL 的 ON CONFLICT DO UPDATE 语法实现原子性 upsert 操作。

        Args:
            commission_rate (float): 佣金费率
            min_commission (float): 最低佣金
            stamp_tax_rate (float): 印花税率
            transfer_fee_rate (float): 过户费率

        Returns:
            dict: 更新后的费率设置字典
        """
        with get_session() as session:
            stmt = pg_insert(SimSetting).values(
                id=1,
                commission_rate=commission_rate,
                min_commission=min_commission,
                stamp_tax_rate=stamp_tax_rate,
                transfer_fee_rate=transfer_fee_rate,
                updated_at=china_now_naive(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "commission_rate": stmt.excluded.commission_rate,
                    "min_commission": stmt.excluded.min_commission,
                    "stamp_tax_rate": stmt.excluded.stamp_tax_rate,
                    "transfer_fee_rate": stmt.excluded.transfer_fee_rate,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)
        return SimSettings.get()

    @staticmethod
    def get_symbol_settings(symbol):
        """
        获取指定标的的费率设置

        Args:
            symbol (str): 股票代码

        Returns:
            dict | None: 标的费率设置字典，包含 symbol、commission_rate、min_commission、
                         stamp_tax_rate、transfer_fee_rate；若不存在则返回 None
        """
        with get_session() as session:
            row = session.query(SimSymbolSetting).filter(
                SimSymbolSetting.symbol == symbol
            ).first()
            if row:
                return {
                    "symbol": row.symbol,                                           # 股票代码
                    "commission_rate": float(row.commission_rate) if row.commission_rate else None,      # 佣金费率
                    "min_commission": float(row.min_commission) if row.min_commission else None,         # 最低佣金
                    "stamp_tax_rate": float(row.stamp_tax_rate) if row.stamp_tax_rate else None,         # 印花税率
                    "transfer_fee_rate": float(row.transfer_fee_rate) if row.transfer_fee_rate else None,  # 过户费率
                }
            return None

    @staticmethod
    def get_all_symbol_settings():
        """
        获取所有标的的费率设置列表

        Returns:
            list[dict]: 所有标的费率设置字典列表，按股票代码排序
        """
        with get_session() as session:
            rows = session.query(SimSymbolSetting).order_by(SimSymbolSetting.symbol).all()
            return [
                {
                    "symbol": r.symbol,                                             # 股票代码
                    "commission_rate": float(r.commission_rate) if r.commission_rate else None,      # 佣金费率
                    "min_commission": float(r.min_commission) if r.min_commission else None,         # 最低佣金
                    "stamp_tax_rate": float(r.stamp_tax_rate) if r.stamp_tax_rate else None,         # 印花税率
                    "transfer_fee_rate": float(r.transfer_fee_rate) if r.transfer_fee_rate else None,  # 过户费率
                }
                for r in rows
            ]

    @staticmethod
    def upsert_symbol_settings(symbol, commission_rate=None, min_commission=None, stamp_tax_rate=None, transfer_fee_rate=None):
        """
        新增或更新指定标的的费率设置

        使用 PostgreSQL 的 ON CONFLICT DO UPDATE 语法实现原子性 upsert 操作。
        参数为 None 的字段会写入数据库 NULL，查询时将回退到全局默认值。

        Args:
            symbol (str): 股票代码
            commission_rate (float | None): 佣金费率，None 表示使用全局值
            min_commission (float | None): 最低佣金，None 表示使用全局值
            stamp_tax_rate (float | None): 印花税率，None 表示使用全局值
            transfer_fee_rate (float | None): 过户费率，None 表示使用全局值

        Returns:
            dict: 更新后的标的费率设置（合并全局默认值）
        """
        with get_session() as session:
            stmt = pg_insert(SimSymbolSetting).values(
                symbol=symbol,
                commission_rate=commission_rate,
                min_commission=min_commission,
                stamp_tax_rate=stamp_tax_rate,
                transfer_fee_rate=transfer_fee_rate,
                updated_at=china_now_naive(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol"],
                set_={
                    "commission_rate": stmt.excluded.commission_rate,
                    "min_commission": stmt.excluded.min_commission,
                    "stamp_tax_rate": stmt.excluded.stamp_tax_rate,
                    "transfer_fee_rate": stmt.excluded.transfer_fee_rate,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)
        return SimSettings.get(symbol)

    @staticmethod
    def delete_symbol_settings(symbol):
        """
        删除指定标的的费率设置

        删除后该标的将回退使用全局默认费率。

        Args:
            symbol (str): 股票代码
        """
        with get_session() as session:
            session.query(SimSymbolSetting).filter(
                SimSymbolSetting.symbol == symbol
            ).delete()
