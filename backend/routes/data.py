"""
数据接口路由

提供 /api/data 和 /api/health 接口。
"""

from datetime import datetime
from flask import Blueprint, jsonify, request
from backend.services.gold_data import get_full_data, build_api_response

# 创建蓝图
bp = Blueprint('data', __name__)

DEFAULT_SYMBOL = "sh518880"


def normalize_symbol(raw: str) -> str:
    """
    将用户输入的股票代码规范化为带前缀的形式。

    Examples
    --------
        '000300'   -> 'sz000300'
        '518880'   -> 'sh518880'
        'sh518880' -> 'sh518880'
        'sz000001' -> 'sz000001'
        '贵州茅台'  -> 'sh600519'  （无法识别中文，返回默认）
    """
    raw = (raw or '').strip()
    if not raw:
        return DEFAULT_SYMBOL
    # 已有前缀，直接返回
    if raw.startswith('sh') or raw.startswith('sz'):
        return raw
    # 纯数字 → 自动补前缀（深交所以 000/001/002/003/开头）
    if len(raw) >= 4 and (
        raw.startswith('000') or raw.startswith('001') or
        raw.startswith('002') or raw.startswith('003')
    ):
        return 'sz' + raw
    return 'sh' + raw


def _normalize_date(value: str) -> datetime:
    """
    将 YYYYMMDD 或 YYYY-MM-DD 格式的字符串转换为 datetime.date。
    转换失败时抛出 ValueError。
    """
    s = str(value).strip()
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, '%Y%m%d')
    return datetime.strptime(s, '%Y-%m-%d')


@bp.route('/api/data')
def api_data():
    """
    返回黄金 ETF 完整技术分析数据。

    Query Parameters
    ---------------
    symbol : str, optional
        股票代码，如 sh518880、sz000300，默认 sh518880。
        用户可输入 518880、000300 等，系统自动补全前缀。
    start_date : str, optional
        开始日期，格式 YYYYMMDD 或 YYYY-MM-DD。
        例如：20240101、2024-01-01
    end_date : str, optional
        结束日期，格式 YYYYMMDD 或 YYYY-MM-DD。
        例如：20260411、2026-04-11

    Response JSON 包含：
    - update_time: 数据更新时间
    - start_date: 请求的开始日期（原始值）
    - end_date: 请求的结束日期（原始值）
    - dates: 日期列表
    - kdata: K线数据 [[开盘,收盘,最低,最高], ...]
    - volume: 成交量列表
    - MA5/MA10/MA20/BB_UPPER/BB_LOWER: 均线及布林带数据
    - MACD/MACD_SIGNAL/MACD_HIST: MACD 指标
    - K/D/J: KDJ 指标
    - RSI: 相对强弱指数
    - 资金净流入/累计净流入: 资金流向
    - latest: 最新指标摘要（卡片数据）
    - signals: 综合分析信号列表
    - symbol: 当前股票代码（规范化后）
    """
    raw = request.args.get('symbol', DEFAULT_SYMBOL)
    symbol = normalize_symbol(raw)
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

    df = get_full_data(symbol=symbol, start_date=start_date, end_date=end_date)
    response = build_api_response(df, symbol=symbol,
                                  start_date=start_date, end_date=end_date)
    response['symbol'] = symbol
    return jsonify(response)


@bp.route('/api/health')
def api_health():
    """健康检查接口"""
    return jsonify({"status": "ok"})
