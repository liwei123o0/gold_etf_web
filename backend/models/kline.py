"""
K线数据模型

使用 SQLite 数据库存储 K 线数据到 instance/ 目录下。
数据表：stock_kline(symbol, date, open, high, low, close, volume)
支持去重写入和按日期范围查询。
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date as date_type
from typing import Optional
import pandas as pd

BASEDIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DB_PATH = os.path.join(BASEDIR, 'instance', 'stock_kline.db')

# 确保 instance 目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_conn():
    conn = _get_db()
    try:
        yield conn
    finally:
        conn.close()


def init_kline_db():
    """初始化 K 线数据表"""
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS stock_kline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(symbol, date)
            )
        ''')
        # 索引加速按 symbol + date 范围查询
        cur.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_date
            ON stock_kline(symbol, date)
        ''')
        conn.commit()
    finally:
        conn.close()


class KlineModel:
    """K线数据管理模型"""

    @staticmethod
    def _parse_date(value) -> str:
        """将日期值统一转换为 YYYYMMDD 字符串"""
        if isinstance(value, (datetime, date_type)):
            return value.strftime('%Y-%m-%d')
        s = str(value).strip()
        # YYYYMMDD -> YYYY-MM-DD
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    @staticmethod
    def _ensure_table():
        """确保数据表已创建"""
        init_kline_db()

    @staticmethod
    def get_latest_date(symbol: str) -> Optional[str]:
        """
        获取数据库中该标的最新日期。

        Parameters
        ----------
        symbol : str
            标的代码，如 sh518880

        Returns
        -------
        str or None
            最新日期（YYYY-MM-DD），无数据时返回 None
        """
        KlineModel._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT MAX(date) as max_date FROM stock_kline WHERE symbol = ?',
                (symbol,)
            )
            row = cur.fetchone()
            return row['max_date'] if row and row['max_date'] else None

    @staticmethod
    def get_cached_data(symbol: str, start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> pd.DataFrame:
        """
        从数据库获取指定日期范围的 K 线数据。

        Parameters
        ----------
        symbol : str
            标的代码
        start_date : str, optional
            开始日期（YYYY-MM-DD 或 YYYYMMDD）
        end_date : str, optional
            结束日期（YYYY-MM-DD 或 YYYYMMDD）

        Returns
        -------
        pd.DataFrame
            列名：'日期','开盘','最高','最低','收盘','成交量'，按日期升序
        """
        KlineModel._ensure_table()

        start = KlineModel._parse_date(start_date) if start_date else None
        end = KlineModel._parse_date(end_date) if end_date else None

        with get_db_conn() as conn:
            cur = conn.cursor()

            if start and end:
                cur.execute(
                    'SELECT date, open, high, low, close, volume '
                    'FROM stock_kline WHERE symbol=? AND date>=? AND date<=? '
                    'ORDER BY date ASC',
                    (symbol, start, end)
                )
            elif start:
                cur.execute(
                    'SELECT date, open, high, low, close, volume '
                    'FROM stock_kline WHERE symbol=? AND date>=? '
                    'ORDER BY date ASC',
                    (symbol, start)
                )
            elif end:
                cur.execute(
                    'SELECT date, open, high, low, close, volume '
                    'FROM stock_kline WHERE symbol=? AND date<=? '
                    'ORDER BY date ASC',
                    (symbol, end)
                )
            else:
                cur.execute(
                    'SELECT date, open, high, low, close, volume '
                    'FROM stock_kline WHERE symbol=? ORDER BY date ASC',
                    (symbol,)
                )

            rows = cur.fetchall()

        if not rows:
            return pd.DataFrame(
                columns=['日期', '开盘', '最高', '最低', '收盘', '成交量']
            )

        df = pd.DataFrame(rows)
        df.columns = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
        return df

    @staticmethod
    def save_data(symbol: str, df: pd.DataFrame) -> int:
        """
        将 DataFrame 保存到数据库，自动去重（INSERT OR REPLACE）。

        Parameters
        ----------
        symbol : str
            标的代码
        df : pd.DataFrame
            必须包含列：'日期','开盘','最高','最低','收盘','成交量'

        Returns
        -------
        int
            写入的记录数
        """
        KlineModel._ensure_table()

        if df is None or df.empty:
            return 0

        records = []
        for _, row in df.iterrows():
            records.append((
                symbol,
                KlineModel._parse_date(row['日期']),
                float(row['开盘']),
                float(row['最高']),
                float(row['最低']),
                float(row['收盘']),
                float(row['成交量']),
            ))

        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.executemany(
                'INSERT OR REPLACE INTO stock_kline '
                '(symbol, date, open, high, low, close, volume) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                records
            )
            conn.commit()
            return cur.rowcount if cur.rowcount else len(records)

    @staticmethod
    def count(symbol: str) -> int:
        """返回数据库中该标的的记录总数"""
        KlineModel._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT COUNT(*) as cnt FROM stock_kline WHERE symbol=?',
                (symbol,)
            )
            return cur.fetchone()['cnt']
