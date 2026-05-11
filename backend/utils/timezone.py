"""
时区处理工具模块

统一使用中国标准时间（UTC+8），提供时区转换和获取当前时间的便捷函数。
所有涉及时区的操作应通过本模块进行，确保全系统时区一致性。
"""

from datetime import datetime, timedelta, timezone


# 中国时区常量（UTC+8），用于全局时区转换
CHINA_TZ = timezone(timedelta(hours=8), 'Asia/Shanghai')


def get_china_now() -> datetime:
    """
    获取当前中国标准时间（UTC+8）

    返回：
        datetime: 带时区信息的当前中国时间
    """
    return datetime.now(CHINA_TZ)


def to_china_time(dt: datetime) -> datetime:
    """
    将任意时区的 datetime 对象转换为中国标准时间（UTC+8）

    参数：
        dt (datetime): 待转换的 datetime 对象，可以是带时区或无时区信息。
            无时区信息时默认视为 UTC 时间。

    返回：
        datetime: 转换后的中国时区 datetime 对象。
            输入为 None 时返回 None。
    """
    if dt is None:
        return None
    # 无时区信息的时间视为 UTC，补充时区后再转换
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CHINA_TZ)


def to_naive_china_time(dt: datetime) -> datetime:
    """
    将 datetime 对象转换为无时区信息的中国本地时间

    适用于需要存入数据库等不支持时区信息的场景。
    转换后去除时区信息，但时间值仍为中国本地时间。

    参数：
        dt (datetime): 待转换的 datetime 对象

    返回：
        datetime: 无时区信息的中国本地时间。
            输入为 None 时返回 None。
    """
    if dt is None:
        return None
    # 先转换为中国时区，再去除时区信息
    return to_china_time(dt).replace(tzinfo=None)


def china_now_naive() -> datetime:
    """
    获取无时区信息的当前中国本地时间

    适用于需要存入数据库等不支持时区信息的场景。
    等价于 to_naive_china_time(get_china_now())。

    返回：
        datetime: 无时区信息的当前中国本地时间
    """
    return to_naive_china_time(get_china_now())
