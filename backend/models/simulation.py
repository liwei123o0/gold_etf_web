"""Sim Trading Models - SQLite persistence"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

BASEDIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DB_PATH = os.path.join(BASEDIR, "instance", "sim_trading.db")

def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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

def init_sim_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS sim_accounts (user_id INTEGER PRIMARY KEY, initial_capital REAL NOT NULL, cash REAL NOT NULL DEFAULT 0, frozen_cash REAL NOT NULL DEFAULT 0, realized_pnl REAL NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cur.execute('CREATE TABLE IF NOT EXISTS sim_positions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, shares INTEGER NOT NULL DEFAULT 0, avg_cost REAL NOT NULL DEFAULT 0, current_price REAL NOT NULL DEFAULT 0, UNIQUE(user_id, symbol))')
        cur.execute('CREATE TABLE IF NOT EXISTS sim_orders (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, direction TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, price REAL NOT NULL, shares INTEGER NOT NULL, commission REAL NOT NULL, pnl REAL NOT NULL DEFAULT 0, trade_type TEXT NOT NULL DEFAULT \'manual\', timestamp TEXT NOT NULL)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON sim_orders(user_id, timestamp DESC)')
        try:
            cur.execute("ALTER TABLE sim_orders ADD COLUMN trade_type TEXT DEFAULT 'manual'")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()

class SimulationAccount:
    @staticmethod
    def _ensure_table():
        init_sim_db()

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return {
            "initial_capital": row["initial_capital"],
            "cash": row["cash"],
            "frozen_cash": row["frozen_cash"],
            "market_value": 0.0,
            "total_assets": row["cash"],
            "unrealized_pnl": 0.0,
            "realized_pnl": row["realized_pnl"],
            "total_pnl": 0.0,
        }

    @classmethod
    def find_by_user_id(cls, user_id):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sim_accounts WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            return cls.from_row(row) if row else None

    @classmethod
    def upsert(cls, user_id, initial_capital, cash, frozen_cash=0.0, realized_pnl=0.0):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sim_accounts (user_id, initial_capital, cash, frozen_cash, realized_pnl, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    initial_capital = excluded.initial_capital,
                    cash = excluded.cash,
                    frozen_cash = excluded.frozen_cash,
                    realized_pnl = excluded.realized_pnl,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, initial_capital, cash, frozen_cash, realized_pnl))
            conn.commit()

    @classmethod
    def delete_by_user_id(cls, user_id):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sim_accounts WHERE user_id = ?", (user_id,))
            conn.commit()


class SimulationPosition:
    @staticmethod
    def _ensure_table():
        init_sim_db()

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        unrealized = (row["current_price"] - row["avg_cost"]) * row["shares"]
        unrealized_pct = (row["current_price"] - row["avg_cost"]) / row["avg_cost"] * 100 if row["avg_cost"] else 0
        return {
            "symbol": row["symbol"],
            "name": row["name"],
            "shares": row["shares"],
            "avg_cost": row["avg_cost"],
            "current_price": row["current_price"],
            "unrealized_pnl": unrealized,
            "unrealized_pnl_pct": unrealized_pct,
        }

    @classmethod
    def find_by_user_id(cls, user_id):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sim_positions WHERE user_id = ? AND shares > 0", (user_id,))
            rows = cur.fetchall()
            return [cls.from_row(r) for r in rows]

    @classmethod
    def upsert(cls, user_id, symbol, name, shares, avg_cost, current_price):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            if shares <= 0:
                cur.execute("DELETE FROM sim_positions WHERE user_id = ? AND symbol = ?", (user_id, symbol))
            else:
                cur.execute("""
                    INSERT INTO sim_positions (user_id, symbol, name, shares, avg_cost, current_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, symbol) DO UPDATE SET
                        name = excluded.name,
                        shares = excluded.shares,
                        avg_cost = excluded.avg_cost,
                        current_price = excluded.current_price
                """, (user_id, symbol, name, shares, avg_cost, current_price))
            conn.commit()

    @classmethod
    def delete_by_user_id(cls, user_id):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sim_positions WHERE user_id = ?", (user_id,))
            conn.commit()


class SimulationOrder:
    @staticmethod
    def _ensure_table():
        init_sim_db()

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return {
            "id": row["id"],
            "direction": row["direction"],
            "symbol": row["symbol"],
            "name": row["name"],
            "price": row["price"],
            "shares": row["shares"],
            "commission": row["commission"],
            "timestamp": row["timestamp"],
            "pnl": row["pnl"],
            "trade_type": row["trade_type"] if "trade_type" in row.keys() else "manual",
        }

    @classmethod
    def find_by_user_id(cls, user_id, limit=50):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM sim_orders WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cur.fetchall()
            return [cls.from_row(r) for r in rows]

    @classmethod
    def insert(cls, order_id, user_id, direction, symbol, name, price, shares, commission, pnl=0, trade_type="manual"):
        cls._ensure_table()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sim_orders (id, user_id, direction, symbol, name, price, shares, commission, pnl, trade_type, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_id, user_id, direction, symbol, name, price, shares, commission, pnl, trade_type, timestamp))
            conn.commit()

    @classmethod
    def delete_by_user_id(cls, user_id):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sim_orders WHERE user_id = ?", (user_id,))
            conn.commit()
