"""
FastAPI 实时行情接口

提供实时行情查询。数据来源：新浪财经（主）、腾讯财经（备）。
"""

import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

# 新浪财经实时行情接口
SINA_URL = "https://hq.sinajs.cn/list={symbols}"
# 腾讯财经实时行情接口
TENCENT_URL = "https://qt.gtimg.cn/q={symbols}"

# 请求头，模拟浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
}


def _normalize_symbol(raw: str) -> str:
    """规范化股票代码"""
    raw = raw.strip()
    if raw.startswith(('sh', 'sz', 'bj')):
        return raw
    if len(raw) >= 4:
        if raw.startswith(('000', '001', '002', '003')):
            return 'sz' + raw
        return 'sh' + raw
    return 'sh' + raw


def _fetch_sina_realtime(symbols: list) -> dict:
    """从新浪财经获取实时行情"""
    sym_str = ",".join(symbols)
    try:
        resp = requests.get(SINA_URL.format(symbols=sym_str), headers=HEADERS, timeout=10)
        resp.encoding = 'gbk'
        return _parse_sina_response(resp.text, symbols)
    except Exception as e:
        return {"error": f"新浪财经获取失败: {str(e)}"}


def _parse_sina_response(text: str, symbols: list) -> dict:
    """解析新浪财经响应"""
    result = {}
    pattern = r'hq_str_(\w+)="([^"]+)"'
    for match in re.finditer(pattern, text):
        sym = match.group(1)
        fields = match.group(2).split(',')
        if len(fields) >= 32:
            result[sym] = _build_realtime_item(fields, 'sina')
    return result


def _build_realtime_item(fields: list, source: str) -> dict:
    """从字段列表构建标准行情数据"""
    try:
        name = fields[0] if len(fields) > 0 else ""
        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[2]) if fields[2] else 0
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        high = float(fields[4]) if fields[4] else 0
        low = float(fields[5]) if fields[5] else 0
        volume = float(fields[8]) if fields[8] else 0
        amount = float(fields[9]) if fields[9] else 0
        open_price = float(fields[1]) if fields[1] else 0
        trade_date = fields[30] if len(fields) > 30 else ""
        trade_time = fields[31] if len(fields) > 31 else ""

        return {
            "name": name,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 3),
            "change_pct": round(change_pct, 2),
            "open": open_price,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "date": trade_date,
            "time": trade_time,
            "source": source,
        }
    except (ValueError, IndexError):
        return {"error": "解析失败", "raw_fields": fields[:10]}


def _fetch_tencent_realtime(symbols: list) -> dict:
    """从腾讯财经获取实时行情（备用）"""
    sym_str = ",".join(symbols)
    try:
        resp = requests.get(TENCENT_URL.format(symbols=sym_str), headers=HEADERS, timeout=10)
        resp.encoding = 'gbk'
        return _parse_tencent_response(resp.text, symbols)
    except Exception as e:
        return {"error": f"腾讯财经获取失败: {str(e)}"}


def _parse_tencent_response(text: str, symbols: list) -> dict:
    """解析腾讯财经响应"""
    result = {}
    for line in text.strip().split('\n'):
        match = re.search(r'="([^"]+)"', line)
        if not match:
            continue
        fields = match.group(1).split('~')
        if len(fields) >= 45:
            sym_match = re.search(r'[vp]_[sq]?(\w+)', line)
            sym = sym_match.group(1) if sym_match else ""
            result[sym] = _build_tencent_item(fields)
    return result


def _build_tencent_item(fields: list) -> dict:
    """从腾讯字段列表构建标准行情数据"""
    try:
        name = fields[1] if len(fields) > 1 else ""
        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[4]) if fields[4] else 0
        open_price = float(fields[5]) if fields[5] else 0
        high = float(fields[33]) if fields[33] else 0
        low = float(fields[34]) if fields[34] else 0
        volume = float(fields[6]) if fields[6] else 0
        amount = fields[37] if len(fields) > 37 else 0
        if amount:
            amount = float(amount)
        else:
            amount = 0

        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        trade_date = fields[30] if len(fields) > 30 else ""
        trade_time = fields[27] if len(fields) > 27 else ""

        return {
            "name": name,
            "price": price,
            "prev_close": prev_close,
            "change": round(change, 3),
            "change_pct": round(change_pct, 2),
            "open": open_price,
            "high": high,
            "low": low,
            "volume": volume,
            "amount": amount,
            "date": trade_date,
            "time": trade_time,
            "source": "tencent",
        }
    except (ValueError, IndexError):
        return {"error": "解析失败", "raw_fields": fields[:10]}


def get_realtime(symbol: str = "sh518880") -> dict:
    """
    获取实时行情

    Args:
        symbol: 股票代码，支持逗号分隔多代码

    Returns:
        dict: 行情数据
    """
    # 支持逗号分隔的多代码
    raw_symbols = [s.strip() for s in symbol.split(',') if s.strip()]
    if not raw_symbols:
        raw_symbols = ["sh518880"]

    symbols = [_normalize_symbol(s) for s in raw_symbols]

    # 先尝试新浪
    result = _fetch_sina_realtime(symbols)
    if 'error' not in result or not result.get('error'):
        return {
            "code": 0,
            "msg": "success",
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": result,
        }

    # 新浪失败，尝试腾讯
    time.sleep(0.3)
    result = _fetch_tencent_realtime(symbols)
    if 'error' not in result or not result.get('error'):
        return {
            "code": 0,
            "msg": "success",
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": result,
        }

    return {
        "code": -1,
        "msg": "获取实时数据失败",
        "error": result.get('error', '未知错误'),
        "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }