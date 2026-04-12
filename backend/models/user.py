"""
用户数据模型
使用 SQLite + Flask-Login 实现用户管理
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from contextlib import contextmanager

BASEDIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DB_PATH = os.path.join(BASEDIR, 'instance', 'users.db')


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


def init_db():
    """初始化用户表"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    finally:
        conn.close()


class User(UserMixin):
    """用户模型"""

    def __init__(self, id, username, password_hash, created_at=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(row['id'], row['username'], row['password_hash'], row['created_at'])

    @classmethod
    def find_by_username(cls, username):
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cur.fetchone()
            return cls.from_row(row)

    @classmethod
    def find_by_id(cls, user_id):
        with get_db_conn() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cur.fetchone()
            return cls.from_row(row)

    @classmethod
    def create(cls, username, password):
        """创建新用户，密码哈希后存入数据库"""
        password_hash = generate_password_hash(password)
        with get_db_conn() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                    (username, password_hash)
                )
                conn.commit()
                user_id = cur.lastrowid
                return cls(user_id, username, password_hash)
            except sqlite3.IntegrityError:
                return None

    def verify_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at
        }
