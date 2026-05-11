"""
K线数据模型

使用 SQLAlchemy ORM 管理 PostgreSQL K 线数据。
数据表：stock_kline(symbol, date, open, high, low, close, volume)
支持去重写入和按日期范围查询。
"""

from datetime import datetime, date as date_type
from typing import Optional

import pandas as pd
from sqlalchemy import Column, Integer, String, Date, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import Base, get_session


class StockKline(Base):
    """
    股票K线数据 ORM 模型

    对应数据库表 stock_kline，存储股票的日K线数据，
    包括开盘价、最高价、最低价、收盘价和成交量。
    唯一约束：(symbol, date)，同一股票同一日期不允许重复。
    """
    __tablename__ = "stock_kline"

    id = Column(Integer, primary_key=True)                                         # 记录ID，主键自增
    symbol = Column(String, nullable=False)                                        # 股票代码
    date = Column(Date, nullable=False)                                            # 交易日期
    open = Column(Numeric, nullable=False)                                         # 开盘价
    high = Column(Numeric, nullable=False)                                         # 最高价
    low = Column(Numeric, nullable=False)                                          # 最低价
    close = Column(Numeric, nullable=False)                                        # 收盘价
    volume = Column(Numeric, nullable=False)                                       # 成交量

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_stock_kline_symbol_date"),
    )


class KlineModel:
    """
    K线数据管理业务操作类

    提供K线数据的查询、保存和统计功能，
    支持按日期范围查询和去重批量写入。
    """

    @staticmethod
    def _parse_date(value) -> str:
        """
        将各种格式的日期值解析为标准格式字符串

        支持的输入格式：
        - datetime/date 对象：直接格式化为 YYYY-MM-DD
        - 8位数字字符串（如 20240101）：转换为 YYYY-MM-DD
        - 其他格式：直接转为字符串

        Args:
            value: 日期值，支持 datetime、date 对象或字符串

        Returns:
            str: 标准格式的日期字符串 (YYYY-MM-DD)
        """
        if isinstance(value, (datetime, date_type)):
            return value.strftime("%Y-%m-%d")
        s = str(value).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    @staticmethod
    def get_latest_date(symbol: str) -> Optional[str]:
        """
        获取指定股票的最新交易日期

        Args:
            symbol (str): 股票代码

        Returns:
            str | None: 最新交易日期字符串 (YYYY-MM-DD)，若无数据则返回 None
        """
        with get_session() as session:
            result = (
                session.query(StockKline.date)
                .filter(StockKline.symbol == symbol)
                .order_by(StockKline.date.desc())
                .first()
            )
            return result.date.strftime("%Y-%m-%d") if result and result.date else None

    @staticmethod
    def get_cached_data(
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        从数据库查询K线数据并返回 DataFrame

        Args:
            symbol (str): 股票代码
            start_date (str | None): 起始日期（含），可选，默认 None
            end_date (str | None): 结束日期（含），可选，默认 None

        Returns:
            pd.DataFrame: K线数据 DataFrame，列名为中文（日期、开盘、最高、最低、收盘、成交量），
                          若无数据则返回空 DataFrame
        """
        start = KlineModel._parse_date(start_date) if start_date else None
        end = KlineModel._parse_date(end_date) if end_date else None

        with get_session() as session:
            query = session.query(
                StockKline.date, StockKline.open, StockKline.high,
                StockKline.low, StockKline.close, StockKline.volume
            ).filter(StockKline.symbol == symbol)

            if start:
                query = query.filter(StockKline.date >= start)
            if end:
                query = query.filter(StockKline.date <= end)

            query = query.order_by(StockKline.date.asc())
            rows = query.all()

        if not rows:
            return pd.DataFrame(columns=["日期", "开盘", "最高", "最低", "收盘", "成交量"])

        data = []
        for r in rows:
            data.append({
                "日期": r.date.strftime("%Y-%m-%d") if hasattr(r.date, "strftime") else str(r.date),
                "开盘": float(r.open),
                "最高": float(r.high),
                "最低": float(r.low),
                "收盘": float(r.close),
                "成交量": float(r.volume),
            })

        df = pd.DataFrame(data)
        df.columns = ["日期", "开盘", "最高", "最低", "收盘", "成交量"]
        return df

    @staticmethod
    def save_data(symbol: str, df: pd.DataFrame) -> int:
        """
        将K线数据批量写入数据库（去重）

        使用 PostgreSQL 的 ON CONFLICT DO NOTHING 语法，
        若 (symbol, date) 已存在则跳过，不更新。

        Args:
            symbol (str): 股票代码
            df (pd.DataFrame): K线数据 DataFrame，需包含列：日期、开盘、最高、最低、收盘、成交量

        Returns:
            int: 尝试写入的记录数（含已存在被跳过的记录）
        """
        if df is None or df.empty:
            return 0

        records = []
        for _, row in df.iterrows():
            records.append({
                "symbol": symbol,
                "date": KlineModel._parse_date(row["日期"]),
                "open": float(row["开盘"]),
                "high": float(row["最高"]),
                "low": float(row["最低"]),
                "close": float(row["收盘"]),
                "volume": float(row["成交量"]),
            })

        with get_session() as session:
            stmt = pg_insert(StockKline).values(records)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["symbol", "date"]
            )
            session.execute(stmt)
            return len(records)

    @staticmethod
    def count(symbol: str) -> int:
        """
        统计指定股票的K线数据记录数

        Args:
            symbol (str): 股票代码

        Returns:
            int: K线数据记录总数
        """
        with get_session() as session:
            return session.query(StockKline).filter(StockKline.symbol == symbol).count()
