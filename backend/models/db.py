"""
SQLAlchemy ORM 数据库连接模块

统一管理 PostgreSQL 数据库引擎、会话工厂和声明式基类，
为整个后端提供数据库连接和会话管理能力。
"""

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# 数据库连接配置字典，包含 PostgreSQL 的连接参数
DB_CONFIG = {
    "dbname": "database",       # 数据库名称
    "user": "root",             # 数据库用户名
    "password": "root",         # 数据库密码
    "host": "localhost",        # 数据库主机地址
    "port": "5432",             # 数据库端口号
}

# PostgreSQL 连接 URL，格式为：postgresql+psycopg2://用户名:密码@主机:端口/数据库名
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

# SQLAlchemy 数据库引擎
# pool_size=5: 连接池保持5个连接
# max_overflow=10: 最多允许额外创建10个连接
# pool_pre_ping=True: 每次从连接池取连接时先检测连接是否存活
engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)

# 会话工厂，用于创建数据库会话实例
# autocommit=False: 不自动提交，需手动调用 commit
# autoflush=False: 不自动刷新，需手动调用 flush
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy 声明式基类，所有 ORM 模型类需继承此类
Base = declarative_base()


@contextmanager
def get_session() -> Session:
    """
    获取数据库会话的上下文管理器

    使用 with 语句自动管理会话的生命周期：
    - 正常执行完毕后自动 commit
    - 发生异常时自动 rollback
    - 无论成功或失败，最终都会 close 会话

    Returns:
        Session: SQLAlchemy 数据库会话对象

    Usage:
        with get_session() as session:
            session.query(Model).all()
    """
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
    """
    FastAPI 依赖注入：每次请求提供一个数据库会话

    用于 FastAPI 路由函数的 Depends 注入，请求结束后自动关闭会话。

    Yields:
        Session: SQLAlchemy 数据库会话对象

    Usage:
        @router.get("/api")
        def api_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
