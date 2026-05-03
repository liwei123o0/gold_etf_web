"""System Settings Model - SQLite persistence"""
import os
import sqlite3
from contextlib import contextmanager

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

def init_settings_table():
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sim_settings (
                id INTEGER PRIMARY KEY,
                commission_rate REAL NOT NULL DEFAULT 0.0003,
                min_commission REAL NOT NULL DEFAULT 5.0,
                stamp_tax_rate REAL NOT NULL DEFAULT 0.001,
                transfer_fee_rate REAL NOT NULL DEFAULT 0.00002,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sim_symbol_settings (
                symbol TEXT PRIMARY KEY,
                commission_rate REAL,
                min_commission REAL,
                stamp_tax_rate REAL,
                transfer_fee_rate REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("SELECT COUNT(*) FROM sim_settings")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO sim_settings (id, commission_rate, min_commission, stamp_tax_rate, transfer_fee_rate) VALUES (1, 0.0003, 5.0, 0.001, 0.00002)")
        conn.commit()
    finally:
        conn.close()

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
        """Get settings, optionally for a specific symbol. Symbol settings override defaults."""
        init_settings_table()
        defaults = SimSettings._get_defaults()
        
        if symbol:
            with get_db_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM sim_symbol_settings WHERE symbol = ?", (symbol,))
                row = cur.fetchone()
                if row:
                    result = defaults.copy()
                    if row["commission_rate"] is not None:
                        result["commission_rate"] = row["commission_rate"]
                    if row["min_commission"] is not None:
                        result["min_commission"] = row["min_commission"]
                    if row["stamp_tax_rate"] is not None:
                        result["stamp_tax_rate"] = row["stamp_tax_rate"]
                    if row["transfer_fee_rate"] is not None:
                        result["transfer_fee_rate"] = row["transfer_fee_rate"]
                    return result
        
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sim_settings WHERE id = 1")
            row = cur.fetchone()
            if row:
                return {
                    "commission_rate": row["commission_rate"],
                    "min_commission": row["min_commission"],
                    "stamp_tax_rate": row["stamp_tax_rate"],
                    "transfer_fee_rate": row["transfer_fee_rate"],
                }
        return defaults

    @staticmethod
    def update(commission_rate, min_commission, stamp_tax_rate, transfer_fee_rate):
        init_settings_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE sim_settings SET
                    commission_rate = ?,
                    min_commission = ?,
                    stamp_tax_rate = ?,
                    transfer_fee_rate = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (commission_rate, min_commission, stamp_tax_rate, transfer_fee_rate))
            conn.commit()
        return SimSettings.get()

    @staticmethod
    def get_symbol_settings(symbol):
        """Get all per-symbol override settings"""
        init_settings_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sim_symbol_settings WHERE symbol = ?", (symbol,))
            row = cur.fetchone()
            if row:
                return {
                    "symbol": row["symbol"],
                    "commission_rate": row["commission_rate"],
                    "min_commission": row["min_commission"],
                    "stamp_tax_rate": row["stamp_tax_rate"],
                    "transfer_fee_rate": row["transfer_fee_rate"],
                }
            return None

    @staticmethod
    def get_all_symbol_settings():
        """Get all per-symbol override settings"""
        init_settings_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sim_symbol_settings ORDER BY symbol")
            rows = cur.fetchall()
            return [
                {
                    "symbol": r["symbol"],
                    "commission_rate": r["commission_rate"],
                    "min_commission": r["min_commission"],
                    "stamp_tax_rate": r["stamp_tax_rate"],
                    "transfer_fee_rate": r["transfer_fee_rate"],
                }
                for r in rows
            ]

    @staticmethod
    def upsert_symbol_settings(symbol, commission_rate=None, min_commission=None, stamp_tax_rate=None, transfer_fee_rate=None):
        """Set per-symbol fee overrides. None means use default."""
        init_settings_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sim_symbol_settings (symbol, commission_rate, min_commission, stamp_tax_rate, transfer_fee_rate, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(symbol) DO UPDATE SET
                    commission_rate = COALESCE(excluded.commission_rate, sim_symbol_settings.commission_rate),
                    min_commission = COALESCE(excluded.min_commission, sim_symbol_settings.min_commission),
                    stamp_tax_rate = COALESCE(excluded.stamp_tax_rate, sim_symbol_settings.stamp_tax_rate),
                    transfer_fee_rate = COALESCE(excluded.transfer_fee_rate, sim_symbol_settings.transfer_fee_rate),
                    updated_at = CURRENT_TIMESTAMP
            """, (symbol, commission_rate, min_commission, stamp_tax_rate, transfer_fee_rate))
            conn.commit()
        return SimSettings.get(symbol)

    @staticmethod
    def delete_symbol_settings(symbol):
        init_settings_table()
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sim_symbol_settings WHERE symbol = ?", (symbol,))
            conn.commit()
