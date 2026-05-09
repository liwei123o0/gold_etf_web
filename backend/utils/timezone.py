"""
时区处理工具
统一使用中国标准时间（UTC+8）
"""
from datetime import datetime, timedelta, timezone


# 中国时区（UTC+8）
CHINA_TZ = timezone(timedelta(hours=8), 'Asia/Shanghai')


def get_china_now() -> datetime:
    """
    获取当前中国标准时间（UTC+8）
    
    Returns:
        当前中国时区的 datetime 对象
    """
    return datetime.now(CHINA_TZ)


def to_china_time(dt: datetime) -> datetime:
    """
    将任意时区的时间转换为中国标准时间（UTC+8）
    
    Args:
        dt: datetime 对象
    
    Returns:
        中国时区的 datetime 对象
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CHINA_TZ)


def to_naive_china_time(dt: datetime) -> datetime:
    """
    转换为无时区信息的中国本地时间（适合存入数据库）
    
    Args:
        dt: datetime 对象
    
    Returns:
        无时区信息的中国本地时间
    """
    if dt is None:
        return None
    return to_china_time(dt).replace(tzinfo=None)


def china_now_naive() -> datetime:
    """
    获取无时区信息的当前中国本地时间（适合存入数据库）
    
    Returns:
        无时区信息的中国本地时间
    """
    return to_naive_china_time(get_china_now())
