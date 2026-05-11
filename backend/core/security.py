"""
JWT 安全工具模块

提供 JWT Token 的创建、验证、解密功能，以及密码哈希和验证功能。
用于用户认证和授权。
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT 密钥（生产环境应从环境变量读取，此处为开发默认值）
SECRET_KEY = "gold-etf-secret-key-change-in-production-2024"
# JWT 加密算法
ALGORITHM = "HS256"
# Token 默认过期时间：24小时（单位：分钟）
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# 密码哈希上下文，使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配

    参数：
        plain_password (str): 用户输入的明文密码
        hashed_password (str): 数据库中存储的哈希密码

    返回：
        bool: 密码匹配返回 True，否则返回 False
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    对明文密码进行哈希加密

    使用 bcrypt 算法生成安全的密码哈希值，用于存储到数据库。

    参数：
        password (str): 明文密码

    返回：
        str: 哈希后的密码字符串
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌

    将用户信息编码为 JWT Token，包含过期时间。

    参数：
        data (Dict[str, Any]): 包含用户信息的字典，如 {"sub": username, "user_id": id}
            - "sub": 用户名（JWT 标准字段，表示主体）
            - "user_id": 用户 ID
        expires_delta (Optional[timedelta]): 自定义的过期时间增量。
            不传则使用默认过期时间（24小时）。

    返回：
        str: 编码后的 JWT Token 字符串
    """
    # 复制数据，避免修改原始字典
    to_encode = data.copy()
    # 计算过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 使用默认过期时间
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 将过期时间写入 payload
    to_encode.update({"exp": expire})
    # 使用 HS256 算法编码生成 JWT Token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码 JWT Token，提取其中的用户信息

    参数：
        token (str): JWT Token 字符串

    返回：
        Optional[Dict[str, Any]]: 解码成功返回包含用户信息的字典，
            如 {"sub": "username", "user_id": 1, "exp": 过期时间戳}；
            解码失败（Token 无效或已过期）返回 None。
    """
    try:
        # 尝试解码 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Token 无效或已过期
        return None


def get_current_user(token: str) -> Optional[Dict[str, Any]]:
    """
    从 JWT Token 中提取当前用户信息

    解码 Token 后提取用户名和用户 ID，用于身份识别。

    参数：
        token (str): JWT Token 字符串

    返回：
        Optional[Dict[str, Any]]: 用户信息字典，格式：
            {"user_id": 用户ID, "username": 用户名}
            Token 无效或缺少必要字段时返回 None。
    """
    # 先解码 Token
    payload = decode_token(token)
    if payload is None:
        return None
    # 提取用户名（JWT 标准的 sub 字段）
    username = payload.get("sub")
    # 提取用户 ID
    user_id = payload.get("user_id")
    # 校验必要字段是否存在
    if username is None or user_id is None:
        return None
    return {"user_id": user_id, "username": username}
