"""
JWT 安全工具模块

提供 JWT token 的创建、验证、解密功能。
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT 配置
SECRET_KEY = "gold-etf-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT token

    Args:
        data: 包含用户信息的字典（如 {"sub": username, "user_id": id}）
        expires_delta: 可选的过期时间delta

    Returns:
        str: JWT token 字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        Optional[Dict]: 解码后的用户信息，失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """
    从 token 获取当前用户信息

    Args:
        token: JWT token 字符串

    Returns:
        Optional[Dict]: 用户信息（包含 user_id, username），失败返回 None
    """
    payload = decode_token(token)
    if payload is None:
        return None
    username = payload.get("sub")
    user_id = payload.get("user_id")
    if username is None or user_id is None:
        return None
    return {"user_id": user_id, "username": username}