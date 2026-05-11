"""
用户数据模型

使用 SQLAlchemy ORM 管理 PostgreSQL 用户表，
提供用户的注册、查询、密码验证等功能。
"""

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, DateTime
from werkzeug.security import generate_password_hash, check_password_hash

from .db import Base, get_session
from ..utils.timezone import china_now_naive


class UserModel(Base):
    """
    用户 ORM 模型

    对应数据库表 users，存储用户的基本信息，
    包括用户名和密码哈希。密码以哈希形式存储，不保存明文。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)                                         # 用户ID，主键自增
    username = Column(String, unique=True, nullable=False)                         # 用户名，唯一约束
    password_hash = Column(String, nullable=False)                                 # 密码哈希值（bcrypt）
    created_at = Column(DateTime, default=china_now_naive)                         # 创建时间

    def to_dict(self):
        """
        将用户 ORM 对象转换为字典格式

        Returns:
            dict: 用户信息字典，包含 id、username 和 created_at
        """
        return {
            "id": self.id,                                                         # 用户ID
            "username": self.username,                                              # 用户名
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,  # 创建时间
        }


class User(UserMixin):
    """
    用户业务模型（兼容 Flask-Login 接口）

    继承 UserMixin 以支持 Flask-Login 的用户认证机制，
    提供用户的查询、创建和密码验证等功能。
    """

    def __init__(self, id, username, password_hash, created_at=None):
        """
        初始化用户业务对象

        Args:
            id (int): 用户ID
            username (str): 用户名
            password_hash (str): 密码哈希值
            created_at (datetime | None): 创建时间，默认 None
        """
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at

    @classmethod
    def from_orm(cls, model):
        """
        从 ORM 模型对象创建用户业务对象

        Args:
            model (UserModel | None): UserModel ORM 对象，若为 None 则返回 None

        Returns:
            User | None: 用户业务对象，若 model 为 None 则返回 None
        """
        if model is None:
            return None
        return cls(model.id, model.username, model.password_hash, model.created_at)

    @classmethod
    def find_by_username(cls, username):
        """
        根据用户名查询用户

        Args:
            username (str): 用户名

        Returns:
            User | None: 用户业务对象，若不存在则返回 None
        """
        with get_session() as session:
            model = session.query(UserModel).filter(UserModel.username == username).first()
            return cls.from_orm(model)

    @classmethod
    def find_by_id(cls, user_id):
        """
        根据用户ID查询用户

        Args:
            user_id (int): 用户ID

        Returns:
            User | None: 用户业务对象，若不存在则返回 None
        """
        with get_session() as session:
            model = session.query(UserModel).filter(UserModel.id == user_id).first()
            return cls.from_orm(model)

    @classmethod
    def create(cls, username, password):
        """
        创建新用户

        对密码进行哈希处理后存入数据库。若用户名已存在（唯一约束冲突），
        则捕获异常并返回 None。

        Args:
            username (str): 用户名
            password (str): 明文密码

        Returns:
            User | None: 新创建的用户业务对象，若创建失败则返回 None
        """
        password_hash = generate_password_hash(password)
        try:
            with get_session() as session:
                model = UserModel(username=username, password_hash=password_hash)
                session.add(model)
                session.flush()
                return cls(model.id, model.username, model.password_hash, model.created_at)
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"[User.create] 创建用户失败: {e}")
            traceback.print_exc()
            return None

    def verify_password(self, password):
        """
        验证密码是否正确

        Args:
            password (str): 待验证的明文密码

        Returns:
            bool: True 表示密码正确，False 表示密码错误
        """
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """
        将用户业务对象转换为字典格式

        Returns:
            dict: 用户信息字典，包含 id、username 和 created_at
        """
        return {
            "id": self.id,                                                         # 用户ID
            "username": self.username,                                              # 用户名
            "created_at": self.created_at,                                          # 创建时间
        }
