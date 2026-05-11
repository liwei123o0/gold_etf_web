"""
数据接口路由模块

提供黄金 ETF 的 K 线数据和技术指标查询接口，以及系统健康检查接口。
接口路径：/api/data、/api/health
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from backend.services.gold_data import get_full_data, build_api_response
from backend.utils.symbol import normalize_symbol

# 创建数据蓝图
bp = Blueprint('data', __name__)

# 默认股票代码：上证黄金ETF（518880）
DEFAULT_SYMBOL = "sh518880"


def _normalize_date(value: str) -> datetime:
    """
    将日期字符串转换为 datetime 对象

    支持的输入格式：
        - YYYYMMDD（如 20240101）
        - YYYY-MM-DD（如 2024-01-01）

    参数：
        value (str): 日期字符串

    返回：
        datetime: 转换后的 datetime 对象

    异常：
        ValueError: 日期格式无法解析时抛出
    """
    s = str(value).strip()
    # 8位纯数字格式：YYYYMMDD
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, '%Y%m%d')
    # 短横线分隔格式：YYYY-MM-DD
    return datetime.strptime(s, '%Y-%m-%d')


@bp.route('/api/data')
def api_data():
    """
    获取黄金 ETF 完整技术分析数据接口

    请求方式：GET
    请求路径：/api/data

    查询参数（Query Parameters）：
        symbol (str, 可选): 股票代码，如 sh518880、sz000300，默认 sh518880。
            用户可输入 518880、000300 等，系统自动补全前缀。
        start_date (str, 可选): 开始日期，格式 YYYYMMDD 或 YYYY-MM-DD。
            例如：20240101、2024-01-01
        end_date (str, 可选): 结束日期，格式 YYYYMMDD 或 YYYY-MM-DD。
            例如：20260411、2026-04-11

    返回值（JSON）：
        - update_time (str): 数据更新时间
        - start_date (str): 请求的开始日期（原始值）
        - end_date (str): 请求的结束日期（原始值）
        - dates (list): 日期列表
        - kdata (list): K线数据，格式 [[开盘, 收盘, 最低, 最高], ...]
        - volume (list): 成交量列表
        - MA5/MA10/MA20/BB_UPPER/BB_LOWER: 均线及布林带数据
        - MACD/MACD_SIGNAL/MACD_HIST: MACD 指标数据
        - K/D/J: KDJ 随机指标数据
        - RSI: 相对强弱指数数据
        - 资金净流入/累计净流入: 资金流向数据
        - latest (dict): 最新指标摘要（卡片数据）
        - signals (list): 综合分析信号列表
        - symbol (str): 当前股票代码（规范化后）

    错误返回：
        HTTP 400: start_date 晚于 end_date，或日期格式错误
    """
    # 获取原始股票代码参数，默认为 sh518880
    raw = request.args.get('symbol', DEFAULT_SYMBOL)
    # 规范化股票代码（补全前缀等）
    symbol = normalize_symbol(raw)
    # 获取可选的日期范围参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # 参数验证：start_date 不能晚于 end_date
    if start_date and end_date:
        try:
            s = _normalize_date(start_date)
            e = _normalize_date(end_date)
            if s and e and s > e:
                return jsonify({'error': 'start_date 不能晚于 end_date'}), 400
        except ValueError as exc:
            return jsonify({'error': f'日期格式错误: {exc}'}), 400

    # 获取完整的历史数据（含技术指标）
    df = get_full_data(symbol=symbol, start_date=start_date, end_date=end_date)
    # 构建 API 响应数据
    response = build_api_response(df, symbol=symbol,
                                  start_date=start_date, end_date=end_date)
    # 将规范化后的股票代码加入响应
    response['symbol'] = symbol
    return jsonify(response)


@bp.route('/api/health')
def api_health():
    """
    系统健康检查接口

    请求方式：GET
    请求路径：/api/health

    请求参数：无

    返回值（JSON）：
        {"status": "ok"}
    """
    return jsonify({"status": "ok"})
