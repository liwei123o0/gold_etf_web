"""
新闻接口路由模块

提供股票相关新闻查询接口。
接口路径：/api/news
"""

from flask import Blueprint, jsonify, request
from backend.services.news import build_news_response

# 创建新闻蓝图
bp = Blueprint('news', __name__)


@bp.route('/api/news')
def api_news():
    """
    获取股票相关新闻列表接口

    请求方式：GET
    请求路径：/api/news

    查询参数（Query Parameters）：
        symbol (str, 可选): 股票代码，如 sh518880、sz000300。
            - 黄金ETF（518880）：返回黄金相关新闻
            - 其他股票：返回该股票相关新闻
            - 不传：返回默认新闻

    返回值（JSON）：
        - news (list): 新闻列表，每项包含：
            - title (str): 新闻标题
            - url (str): 新闻链接
            - time (str): 发布时间
            - source (str): 新闻来源
        - update_time (str): 数据更新时间
    """
    # 从查询参数获取股票代码
    symbol = request.args.get('symbol')
    # 调用新闻服务构建响应数据
    return jsonify(build_news_response(symbol=symbol))
