"""System Settings Model - SQLAlchemy ORM persistence"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import Base, get_session


class SimSetting(Base):
    __tablename__ = "sim_settings"

    id = Column(Integer, primary_key=True)
    commission_rate = Column(Numeric, nullable=False, default=0.0003)
    min_commission = Column(Numeric, nullable=False, default=5.0)
    stamp_tax_rate = Column(Numeric, nullable=False, default=0.001)
    transfer_fee_rate = Column(Numeric, nullable=False, default=0.00002)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SimSymbolSetting(Base):
    __tablename__ = "sim_symbol_settings"

    symbol = Column(String, primary_key=True)
    commission_rate = Column(Numeric, nullable=True)
    min_commission = Column(Numeric, nullable=True)
    stamp_tax_rate = Column(Numeric, nullable=True)
    transfer_fee_rate = Column(Numeric, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SimSettings:
    @staticmethod
    def _get_defaults():
        return {
            "commission_rate": 0.0003,
            "min_commission": 5.0,
            "stamp_tax_rate": 0.001,
            "transfer_fee_rate": 0.00002,
        }

    @staticmethod
    def get(symbol=None):
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
        with get_session() as session:
            stmt = pg_insert(SimSetting).values(
                id=1,
                commission_rate=commission_rate,
                min_commission=min_commission,
                stamp_tax_rate=stamp_tax_rate,
                transfer_fee_rate=transfer_fee_rate,
                updated_at=datetime.utcnow(),
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
        with get_session() as session:
            row = session.query(SimSymbolSetting).filter(
                SimSymbolSetting.symbol == symbol
            ).first()
            if row:
                return {
                    "symbol": row.symbol,
                    "commission_rate": float(row.commission_rate) if row.commission_rate else None,
                    "min_commission": float(row.min_commission) if row.min_commission else None,
                    "stamp_tax_rate": float(row.stamp_tax_rate) if row.stamp_tax_rate else None,
                    "transfer_fee_rate": float(row.transfer_fee_rate) if row.transfer_fee_rate else None,
                }
            return None

    @staticmethod
    def get_all_symbol_settings():
        with get_session() as session:
            rows = session.query(SimSymbolSetting).order_by(SimSymbolSetting.symbol).all()
            return [
                {
                    "symbol": r.symbol,
                    "commission_rate": float(r.commission_rate) if r.commission_rate else None,
                    "min_commission": float(r.min_commission) if r.min_commission else None,
                    "stamp_tax_rate": float(r.stamp_tax_rate) if r.stamp_tax_rate else None,
                    "transfer_fee_rate": float(r.transfer_fee_rate) if r.transfer_fee_rate else None,
                }
                for r in rows
            ]

    @staticmethod
    def upsert_symbol_settings(symbol, commission_rate=None, min_commission=None, stamp_tax_rate=None, transfer_fee_rate=None):
        with get_session() as session:
            stmt = pg_insert(SimSymbolSetting).values(
                symbol=symbol,
                commission_rate=commission_rate,
                min_commission=min_commission,
                stamp_tax_rate=stamp_tax_rate,
                transfer_fee_rate=transfer_fee_rate,
                updated_at=datetime.utcnow(),
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
        with get_session() as session:
            session.query(SimSymbolSetting).filter(
                SimSymbolSetting.symbol == symbol
            ).delete()
