"""
SQLAlchemy ORM 数据库连接模块
统一管理 PostgreSQL 引擎、会话和声明式基类
"""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

DB_CONFIG = {
    "dbname": "database",
    "user": "root",
    "password": "root",
    "host": "localhost",
    "port": "5432",
}

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_session() -> Session:
    """获取数据库会话上下文管理器"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI 依赖注入：每次请求提供一个数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
