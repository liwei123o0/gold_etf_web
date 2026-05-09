"""
用户数据模型
使用 SQLAlchemy ORM 管理 PostgreSQL 用户表
"""

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, DateTime
from werkzeug.security import generate_password_hash, check_password_hash

from .db import Base, get_session


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }


class User(UserMixin):
    """用户业务模型（兼容原有接口）"""

    def __init__(self, id, username, password_hash, created_at=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at

    @classmethod
    def from_orm(cls, model):
        if model is None:
            return None
        return cls(model.id, model.username, model.password_hash, model.created_at)

    @classmethod
    def find_by_username(cls, username):
        with get_session() as session:
            model = session.query(UserModel).filter(UserModel.username == username).first()
            return cls.from_orm(model)

    @classmethod
    def find_by_id(cls, user_id):
        with get_session() as session:
            model = session.query(UserModel).filter(UserModel.id == user_id).first()
            return cls.from_orm(model)

    @classmethod
    def create(cls, username, password):
        password_hash = generate_password_hash(password)
        try:
            with get_session() as session:
                model = UserModel(username=username, password_hash=password_hash)
                session.add(model)
                session.flush()
                return cls(model.id, model.username, model.password_hash, model.created_at)
        except Exception:
            return None

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at,
        }
