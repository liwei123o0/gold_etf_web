"""
实时行情数据获取模块

提供从外部数据源获取股票实时行情的功能。
数据源优先级：新浪财经（主）→ 腾讯财经（备用）。
支持多代码批量查询。
"""

import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

from backend.utils.symbol import normalize_symbol

# 新浪财经实时行情接口 URL 模板，{symbols} 替换为逗号分隔的股票代码
SINA_URL = "https://hq.sinajs.cn/list={symbols}"
# 腾讯财经实时行情接口 URL 模板，{symbols} 替换为逗号分隔的股票代码
TENCENT_URL = "https://qt.gtimg.cn/q={symbols}"

# HTTP 请求头，模拟浏览器访问以避免被反爬虫拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
}


def _fetch_sina_realtime(symbols: list) -> dict:
    """
    从新浪财经获取实时行情数据

    参数：
        symbols (list): 股票代码列表，如 ['sh518880', 'sz000300']

    返回：
        dict: 键为股票代码，值为行情数据字典；失败时返回 {"error": "错误信息"}
    """
    # 将股票代码列表拼接为逗号分隔的字符串
    sym_str = ",".join(symbols)
    try:
        # 发送 GET 请求获取行情数据
        resp = requests.get(SINA_URL.format(symbols=sym_str), headers=HEADERS, timeout=10)
        # 新浪接口返回 GBK 编码，需要手动设置
        resp.encoding = 'gbk'
        # 解析响应文本
        return _parse_sina_response(resp.text, symbols)
    except Exception as e:
        return {"error": f"新浪财经获取失败: {str(e)}"}


def _parse_sina_response(text: str, symbols: list) -> dict:
    """
    解析新浪财经实时行情响应文本

    新浪接口返回格式示例：
        var hq_str_sh518880="黄金ETF,5.350,5.330,...";

    参数：
        text (str): 新浪接口返回的原始文本
        symbols (list): 请求的股票代码列表

    返回：
        dict: 键为股票代码，值为标准化的行情数据字典
    """
    result = {}
    # 使用正则匹配 hq_str_代码="字段1,字段2,..." 的格式
    pattern = r'hq_str_(\w+)="([^"]+)"'
    for match in re.finditer(pattern, text):
        sym = match.group(1)  # 股票代码
        fields = match.group(2).split(',')  # 逗号分隔的字段列表
        # 新浪接口至少需要 32 个字段才能完整解析
        if len(fields) >= 32:
            result[sym] = _build_realtime_item(fields, 'sina')
    return result


def _build_realtime_item(fields: list, source: str) -> dict:
    """
    从新浪财经字段列表构建标准化的行情数据字典

    新浪字段索引说明：
        [0] 名称, [1] 今开, [2] 昨收, [3] 当前价, [4] 最高, [5] 最低,
        [8] 成交量, [9] 成交额, [30] 日期, [31] 时间

    参数：
        fields (list): 逗号分隔的字段列表
        source (str): 数据来源标识，如 'sina'

    返回：
        dict: 标准化的行情数据字典
    """
    try:
        name = fields[0] if len(fields) > 0 else ""  # 股票名称
        price = float(fields[3]) if fields[3] else 0  # 当前价格
        prev_close = float(fields[2]) if fields[2] else 0  # 昨日收盘价
        change = price - prev_close  # 涨跌额
        change_pct = (change / prev_close * 100) if prev_close else 0  # 涨跌幅（%）
        high = float(fields[4]) if fields[4] else 0  # 最高价
        low = float(fields[5]) if fields[5] else 0  # 最低价
        volume = float(fields[8]) if fields[8] else 0  # 成交量（手）
        amount = float(fields[9]) if fields[9] else 0  # 成交额（元）
        open_price = float(fields[1]) if fields[1] else 0  # 今日开盘价
        trade_date = fields[30] if len(fields) > 30 else ""  # 交易日期
        trade_time = fields[31] if len(fields) > 31 else ""  # 交易时间

        return {
            "name": name,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 3),  # 涨跌额，保留3位小数
            "change_pct": round(change_pct, 2),  # 涨跌幅，保留2位小数
            "open": open_price,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "date": trade_date,
            "time": trade_time,
            "source": source,  # 数据来源标识
        }
    except (ValueError, IndexError):
        # 字段解析失败，返回错误信息和原始字段（前10个）
        return {"error": "解析失败", "raw_fields": fields[:10]}


def _fetch_tencent_realtime(symbols: list) -> dict:
    """
    从腾讯财经获取实时行情数据（备用数据源）

    参数：
        symbols (list): 股票代码列表

    返回：
        dict: 键为股票代码，值为行情数据字典；失败时返回 {"error": "错误信息"}
    """
    # 将股票代码列表拼接为逗号分隔的字符串
    sym_str = ",".join(symbols)
    try:
        resp = requests.get(TENCENT_URL.format(symbols=sym_str), headers=HEADERS, timeout=10)
        # 腾讯接口同样使用 GBK 编码
        resp.encoding = 'gbk'
        return _parse_tencent_response(resp.text, symbols)
    except Exception as e:
        return {"error": f"腾讯财经获取失败: {str(e)}"}


def _parse_tencent_response(text: str, symbols: list) -> dict:
    """
    解析腾讯财经实时行情响应文本

    腾讯接口返回格式示例：
        v_sh518880="1~黄金ETF~518880~5.35~...";

    参数：
        text (str): 腾讯接口返回的原始文本
        symbols (list): 请求的股票代码列表

    返回：
        dict: 键为股票代码，值为标准化的行情数据字典
    """
    result = {}
    for line in text.strip().split('\n'):
        # 提取等号后引号内的内容
        match = re.search(r'="([^"]+)"', line)
        if not match:
            continue
        # 腾讯接口使用 ~ 作为字段分隔符
        fields = match.group(1).split('~')
        # 至少需要 45 个字段才能完整解析
        if len(fields) >= 45:
            # 从行首提取股票代码
            sym_match = re.search(r'[vp]_[sq]?(\w+)', line)
            sym = sym_match.group(1) if sym_match else ""
            result[sym] = _build_tencent_item(fields)
    return result


def _build_tencent_item(fields: list) -> dict:
    """
    从腾讯财经字段列表构建标准化的行情数据字典

    腾讯字段索引说明：
        [1] 名称, [3] 当前价, [4] 昨收, [5] 今开,
        [6] 成交量, [27] 时间, [30] 日期,
        [33] 最高, [34] 最低, [37] 成交额

    参数：
        fields (list): 波浪号分隔的字段列表

    返回：
        dict: 标准化的行情数据字典
    """
    try:
        name = fields[1] if len(fields) > 1 else ""  # 股票名称
        price = float(fields[3]) if fields[3] else 0  # 当前价格
        prev_close = float(fields[4]) if fields[4] else 0  # 昨日收盘价
        open_price = float(fields[5]) if fields[5] else 0  # 今日开盘价
        high = float(fields[33]) if fields[33] else 0  # 最高价
        low = float(fields[34]) if fields[34] else 0  # 最低价
        volume = float(fields[6]) if fields[6] else 0  # 成交量
        amount = fields[37] if len(fields) > 37 else 0  # 成交额
        if amount:
            amount = float(amount)
        else:
            amount = 0

        change = price - prev_close  # 涨跌额
        change_pct = (change / prev_close * 100) if prev_close else 0  # 涨跌幅（%）
        trade_date = fields[30] if len(fields) > 30 else ""  # 交易日期
        trade_time = fields[27] if len(fields) > 27 else ""  # 交易时间

        return {
            "name": name,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 3),  # 涨跌额，保留3位小数
            "change_pct": round(change_pct, 2),  # 涨跌幅，保留2位小数
            "open": open_price,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "date": trade_date,
            "time": trade_time,
            "source": "tencent",  # 数据来源标识
        }
    except (ValueError, IndexError):
        # 字段解析失败，返回错误信息和原始字段（前10个）
        return {"error": "解析失败", "raw_fields": fields[:10]}


def get_realtime(symbol: str = "sh518880") -> dict:
    """
    获取实时行情数据（主入口函数）

    优先使用新浪财经数据源，若失败则自动切换到腾讯财经备用数据源。

    参数：
        symbol (str): 股票代码，支持逗号分隔的多代码查询，如 "sh518880,sz000300"。
            默认为 "sh518880"。

    返回：
        dict: 行情数据字典，格式如下：
            成功时：
                {
                    "code": 0,
                    "msg": "success",
                    "update_time": "2024-01-01 15:00:00",
                    "data": {股票代码: 行情数据字典, ...}
                }
            失败时：
                {
                    "code": -1,
                    "msg": "获取实时数据失败",
                    "error": "错误信息",
                    "update_time": "2024-01-01 15:00:00"
                }
    """
    # 支持逗号分隔的多代码查询
    raw_symbols = [s.strip() for s in symbol.split(',') if s.strip()]
    if not raw_symbols:
        raw_symbols = ["sh518880"]

    # 对每个股票代码进行规范化（补全前缀）
    symbols = [normalize_symbol(s) for s in raw_symbols]

    # 优先尝试新浪财经数据源
    result = _fetch_sina_realtime(symbols)
    if 'error' not in result or not result.get('error'):
        return {
            "code": 0,
            "msg": "success",
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": result,
        }

    # 新浪失败，等待 0.3 秒后尝试腾讯财经备用数据源
    time.sleep(0.3)
    result = _fetch_tencent_realtime(symbols)
    if 'error' not in result or not result.get('error'):
        return {
            "code": 0,
            "msg": "success",
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": result,
        }

    # 两个数据源均失败，返回错误
    return {
        "code": -1,
        "msg": "获取实时数据失败",
        "error": result.get('error', '未知错误'),
        "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
