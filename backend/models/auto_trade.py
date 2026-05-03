"""Auto Trade Task Model - SQLite persistence, per-symbol tasks"""
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

def init_auto_trade_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS auto_trade_tasks (
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL DEFAULT 'grid',
                grid_count INTEGER DEFAULT 10,
                grid_spread REAL DEFAULT 0.10,
                base_ma_key TEXT DEFAULT 'MA20',
                macd_ma_key TEXT DEFAULT NULL,
                position_size REAL DEFAULT 1.0,
                check_interval INTEGER DEFAULT 30,
                allocated_funds REAL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 0,
                last_check TEXT DEFAULT NULL,
                last_signal TEXT DEFAULT NULL,
                task_cash REAL DEFAULT 0,
                task_pnl REAL DEFAULT 0,
                position_shares INTEGER DEFAULT 0,
                position_avg_cost REAL DEFAULT 0,
                task_name TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, symbol)
            )
        """)
        # Migration: add runtime columns if missing
        try:
            cur.execute("ALTER TABLE auto_trade_tasks ADD COLUMN task_cash REAL DEFAULT 0")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE auto_trade_tasks ADD COLUMN task_pnl REAL DEFAULT 0")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE auto_trade_tasks ADD COLUMN position_shares INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE auto_trade_tasks ADD COLUMN position_avg_cost REAL DEFAULT 0")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE auto_trade_tasks ADD COLUMN task_name TEXT DEFAULT ''")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()

class AutoTradeTask:
    @staticmethod
    def _ensure_table():
        init_auto_trade_db()

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return {
            "user_id": row["user_id"],
            "symbol": row["symbol"],
            "strategy": row["strategy"],
            "grid_count": row["grid_count"],
            "grid_spread": row["grid_spread"],
            "base_ma_key": row["base_ma_key"],
            "macd_ma_key": row["macd_ma_key"],
            "position_size": row["position_size"],
            "check_interval": row["check_interval"],
            "allocated_funds": row["allocated_funds"] or 0,
            "enabled": bool(row["enabled"]),
            "last_check": row["last_check"],
            "last_signal": row["last_signal"],
            "task_cash": row["task_cash"] if "task_cash" in row.keys() else row["allocated_funds"],
            "task_pnl": row["task_pnl"] if "task_pnl" in row.keys() else 0,
            "position_shares": row["position_shares"] if "position_shares" in row.keys() else 0,
            "position_avg_cost": row["position_avg_cost"] if "position_avg_cost" in row.keys() else 0,
            "task_name": row["task_name"] if "task_name" in row.keys() else row["symbol"],
            "unrealized_pnl": row["unrealized_pnl"] if "unrealized_pnl" in row.keys() else 0,
        }

    @classmethod
    def find_by_user(cls, user_id):
        """Get all tasks for a user"""
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM auto_trade_tasks WHERE user_id = ? ORDER BY symbol",
                (user_id,)
            )
            rows = cur.fetchall()
            return [cls.from_row(r) for r in rows]

    @classmethod
    def find_by_symbol(cls, user_id, symbol):
        """Get a specific task"""
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM auto_trade_tasks WHERE user_id = ? AND symbol = ?",
                (user_id, symbol)
            )
            row = cur.fetchone()
            return cls.from_row(row) if row else None

    @classmethod
    def upsert(cls, user_id, symbol, config: dict):
        """Create or update a task"""
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO auto_trade_tasks
                    (user_id, symbol, strategy, grid_count, grid_spread,
                     base_ma_key, macd_ma_key, position_size, check_interval,
                     allocated_funds, enabled, last_check, last_signal,
                     task_cash, task_pnl, position_shares, position_avg_cost,
                     unrealized_pnl, task_name, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, symbol) DO UPDATE SET
                    strategy = excluded.strategy,
                    grid_count = excluded.grid_count,
                    grid_spread = excluded.grid_spread,
                    base_ma_key = excluded.base_ma_key,
                    macd_ma_key = excluded.macd_ma_key,
                    position_size = excluded.position_size,
                    check_interval = excluded.check_interval,
                    allocated_funds = excluded.allocated_funds,
                    enabled = excluded.enabled,
                    last_check = excluded.last_check,
                    last_signal = excluded.last_signal,
                    task_cash = excluded.task_cash,
                    task_pnl = excluded.task_pnl,
                    position_shares = excluded.position_shares,
                    position_avg_cost = excluded.position_avg_cost,
                    unrealized_pnl = excluded.unrealized_pnl,
                    task_name = excluded.task_name,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user_id,
                symbol,
                config.get("strategy", "grid"),
                config.get("grid_count", 10),
                config.get("grid_spread", 0.10),
                config.get("base_ma_key", "MA20"),
                config.get("macd_ma_key"),
                config.get("position_size", 1.0),
                config.get("check_interval", 30),
                config.get("allocated_funds", 0),
                1 if config.get("enabled") else 0,
                config.get("last_check"),
                config.get("last_signal"),
                config.get("task_cash", config.get("allocated_funds", 0)),
                config.get("task_pnl", 0),
                config.get("position_shares", 0),
                config.get("position_avg_cost", 0),
                config.get("unrealized_pnl", 0),
                config.get("task_name", symbol),
            ))
            conn.commit()

    @classmethod
    def update_enabled(cls, user_id, symbol, enabled: bool):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO auto_trade_tasks (user_id, symbol, enabled, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, symbol) DO UPDATE SET
                    enabled = excluded.enabled,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, symbol, 1 if enabled else 0))
            conn.commit()

    @classmethod
    def update_last_check(cls, user_id, symbol, last_check: str, last_signal: str = None):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE auto_trade_tasks
                SET last_check = ?, last_signal = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND symbol = ?
            """, (last_check, last_signal, user_id, symbol))
            conn.commit()

    @classmethod
    def update_runtime(cls, user_id, symbol, task_cash: float, task_pnl: float,
                       position_shares: int, position_avg_cost: float,
                       unrealized_pnl: float = 0, task_name: str = None):
        """Persist runtime state to DB"""
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE auto_trade_tasks
                SET task_cash = ?, task_pnl = ?, position_shares = ?,
                    position_avg_cost = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP
                    , task_name = COALESCE(?, task_name)
                WHERE user_id = ? AND symbol = ?
            """, (task_cash, task_pnl, position_shares, position_avg_cost,
                  unrealized_pnl, task_name, user_id, symbol))
            conn.commit()

    @classmethod
    def total_allocated_funds(cls, user_id):
        """Get sum of allocated_funds for all tasks of a user"""
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(SUM(allocated_funds), 0) FROM auto_trade_tasks WHERE user_id = ?",
                (user_id,)
            )
            row = cur.fetchone()
            return row[0] if row else 0

    @classmethod
    def delete_task(cls, user_id, symbol):
        cls._ensure_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM auto_trade_tasks WHERE user_id = ? AND symbol = ?",
                (user_id, symbol)
            )
            conn.commit()
