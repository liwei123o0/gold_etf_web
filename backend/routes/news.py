"""
新闻接口路由

提供 /api/news 接口，支持 ?symbol=xxx 参数。
"""

from flask import Blueprint, jsonify, request
from backend.services.news import build_news_response

# 创建蓝图
bp = Blueprint('news', __name__)


@bp.route('/api/news')
def api_news():
    """
    返回相关新闻列表，支持 ?symbol=xxx 参数。

    - 黄金ETF(518880)：返回黄金新闻
    - 其他股票：返回该股票的新闻

    Query Parameters
    ----------------
    symbol : str, optional
        股票代码，如 sh518880、sz000300

    Response JSON 包含：
    - news: 新闻列表，每项含 title/url/time/source
    - update_time: 更新时间
    """
    symbol = request.args.get('symbol')
    return jsonify(build_news_response(symbol=symbol))
