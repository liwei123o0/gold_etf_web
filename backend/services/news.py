"""
新闻获取服务

从 AKShare 获取黄金/股票相关新闻，失败时返回默认静态资讯。
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# 默认静态资讯（AKShare 不可用时的兜底数据）
DEFAULT_NEWS: List[Dict[str, str]] = [
    {
        'title': '黄金价格受美元走弱支撑维持高位',
        'url': 'https://finance.sina.com.cn/gold/',
        'time': '今日',
        'source': '市场动态',
    },
    {
        'title': '各国央行持续购金 新兴市场成主力',
        'url': 'https://finance.sina.com.cn/gold/',
        'time': '今日',
        'source': '央行观察',
    },
    {
        'title': '地缘风险升温 避险买盘支撑金价',
        'url': 'https://finance.sina.com.cn/gold/',
        'time': '今日',
        'source': '避险情绪',
    },
    {
        'title': '美联储利率预期调整 金价波动加大',
        'url': 'https://finance.sina.com.cn/gold/',
        'time': '今日',
        'source': '美联储动态',
    },
]

# 黄金ETF代码
GOLD_ETF_CODES = {'518880', 'sh518880'}


def _extract_numeric(symbol: str) -> str:
    """提取纯数字代码"""
    return symbol.replace('sh', '').replace('sz', '')


def get_gold_news() -> List[Dict[str, str]]:
    """
    获取黄金相关新闻。

    优先使用 AKShare 接口，失败时返回默认静态资讯。

    Returns
    -------
    List[Dict[str, str]]
        每项包含 keys: title, url, time, source
    """
    try:
        import akshare as ak
        df = ak.stock_news_em(symbol='黄金')
        news_list: List[Dict[str, str]] = []
        for _, row in df.head(10).iterrows():
            news_list.append({
                'title': row['新闻标题'],
                'url': row['新闻链接'],
                'time': str(row['发布时间'])[:16] if pd.notna(row['发布时间']) else '',
                'source': row['文章来源'] if pd.notna(row['文章来源']) else '未知',
            })
        return news_list
    except Exception:
        return DEFAULT_NEWS


def get_stock_news(symbol: str) -> List[Dict[str, str]]:
    """
    根据股票代码获取相关新闻。

    - 黄金ETF（518880）：返回黄金新闻
    - 其他股票：通过 akshare 的 stock_news_em 获取

    Parameters
    ----------
    symbol : str
        股票代码，如 sh518880、sz000300、000300

    Returns
    -------
    List[Dict[str, str]]
        每项包含 keys: title, url, time, source
    """
    numeric = _extract_numeric(symbol)

    # 黄金ETF
    if numeric == '518880':
        return get_gold_news()

    # 通过 akshare 获取个股新闻
    try:
        import akshare as ak
        # 尝试用纯数字代码
        df = ak.stock_news_em(symbol=numeric)
        news_list: List[Dict[str, str]] = []
        for _, row in df.head(10).iterrows():
            news_list.append({
                'title': row['新闻标题'],
                'url': row['新闻链接'],
                'time': str(row['发布时间'])[:16] if pd.notna(row['发布时间']) else '',
                'source': row['文章来源'] if pd.notna(row['文章来源']) else '未知',
            })
        return news_list if news_list else DEFAULT_NEWS
    except Exception:
        return DEFAULT_NEWS


def build_news_response(symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    构建新闻 API 响应。

    Parameters
    ----------
    symbol : str, optional
        股票代码，无则默认黄金ETF

    Returns
    -------
    Dict
        包含 news 列表和 update_time
    """
    news = get_stock_news(symbol) if symbol else get_gold_news()
    return {
        'news': news,
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
