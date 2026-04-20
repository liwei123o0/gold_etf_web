"""
实时行情接口

提供 /api/realtime 实时行情查询。
数据来源：新浪财经（主）、腾讯财经（备）。
"""

import re
import time

import logging
import requests
from flask import Blueprint, jsonify, request
from datetime import datetime

bp = Blueprint('realtime', __name__)

DEFAULT_SYMBOL = "sh518880"

# 新浪财经实时行情接口
SINA_URL = "https://hq.sinajs.cn/list={symbols}"
# 腾讯财经实时行情接口
TENCENT_URL = "https://qt.gtimg.cn/q={symbols}"

# 请求头，模拟浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
}


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
    # 格式: var hq_str_sh518880="名称,现价,涨跌,涨跌幅,成交量,成交额,..."
    pattern = r'hq_str_(\w+)="([^"]+)"'
    for match in re.finditer(pattern, text):
        sym = match.group(1)
        fields = match.group(2).split(',')
        if len(fields) >= 32:
            result[sym] = _build_realtime_item(fields, 'sina')
    logging.info(f"{result}")
    return result


def _build_realtime_item(fields: list, source: str) -> dict:
    """从字段列表构建标准行情数据"""
    try:
        name = fields[0] if len(fields) > 0 else ""
        # 新浪字段索引 (主要):
        # 0:名称 1:今开 2:昨收 3:现价 4:最高 5:最低
        # 6:买一价 7:卖一价 8:成交量(股) 9:成交额(元)
        # 10:买一量 11:买一价 12:买二量 13:买二价 ... 以此类推
        # 31:时间 32:日期
        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[2]) if fields[2] else 0
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
        high = float(fields[4]) if fields[4] else 0
        low = float(fields[5]) if fields[5] else 0
        volume = float(fields[8]) if fields[8] else 0  # 成交量(股)
        amount = float(fields[9]) if fields[9] else 0  # 成交额(元)
        open_price = float(fields[1]) if fields[1] else 0

        # 时间/日期
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
    except (ValueError, IndexError) as e:
        return {"error": f"解析失败: {str(e)}", "raw_fields": fields[:10]}


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
    # 格式: v_pv_518880="...data..." 或 pv_518880="...data..."
    # 实际格式: pv_s_sh518880="...data..."
    for line in text.strip().split('\n'):
        match = re.search(r'="([^"]+)"', line)
        if not match:
            continue
        fields = match.group(1).split('~')
        if len(fields) >= 45:
            # 提取代码
            sym_match = re.search(r'[vp]_[sq]?(\w+)', line)
            sym = sym_match.group(1) if sym_match else ""
            result[sym] = _build_tencent_item(fields)
    return result


def _build_tencent_item(fields: list) -> dict:
    """从腾讯字段列表构建标准行情数据"""
    try:
        # 腾讯字段 (主要):
        # 0:名称 1:代码 2:现价 3:昨收 4:今开 5:成交量
        # 6:外盘 7:内盘 8:买一价 9:买一量 ... 19:卖一价 20:卖一量
        # 21-24:涨跌相关 27:时间 30:日期 31-34:实时行情
        name = fields[1] if len(fields) > 1 else ""
        price = float(fields[3]) if fields[3] else 0
        prev_close = float(fields[4]) if fields[4] else 0
        open_price = float(fields[5]) if fields[5] else 0
        high = float(fields[33]) if fields[33] else 0
        low = float(fields[34]) if fields[34] else 0
        volume = float(fields[6]) if fields[6] else 0
        amount = float(fields[37]) if fields[37] else 0 if len(fields) > 37 else 0

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
    except (ValueError, IndexError) as e:
        return {"error": f"解析失败: {str(e)}", "raw_fields": fields[:10]}


@bp.route('/api/realtime')
def api_realtime():
    """
    获取实时行情数据。

    Query Parameters
    ---------------
    symbol : str, optional
        股票代码，如 sh518880、sz000300，默认 sh518880。
        支持多代码，用逗号分隔，如 sh518880,sz000300。
    """
    raw = request.args.get('symbol', DEFAULT_SYMBOL)
    # 支持逗号分隔的多代码
    raw_symbols = [s.strip() for s in raw.split(',') if s.strip()]
    if not raw_symbols:
        raw_symbols = [DEFAULT_SYMBOL]

    # 规范化代码
    def normalize(sym):
        sym = sym.strip()
        if sym.startswith(('sh', 'sz', 'bj')):
            return sym
        if len(sym) >= 4:
            if sym.startswith(('000', '001', '002', '003')):
                return 'sz' + sym
            return 'sh' + sym
        return 'sh' + sym

    symbols = [normalize(s) for s in raw_symbols]

    # 先尝试新浪
    result = _fetch_sina_realtime(symbols)
    if 'error' not in result or not result.get('error'):
        return jsonify({
            "code": 0,
            "msg": "success",
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": result,
        })

    # 新浪失败，尝试腾讯
    time.sleep(0.3)
    result = _fetch_tencent_realtime(symbols)
    if 'error' not in result or not result.get('error'):
        return jsonify({
            "code": 0,
            "msg": "success",
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": result,
        })

    return jsonify({
        "code": -1,
        "msg": "获取实时数据失败",
        "error": result.get('error', '未知错误'),
        "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }), 500