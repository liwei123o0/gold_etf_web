"""
backend.services 包：业务逻辑层
"""
from backend.services.gold_data import (
    fetch_etf_kline,
    get_full_data,
    generate_signals,
    build_api_response,
)
from backend.services.news import get_gold_news, build_news_response

__all__ = [
    'fetch_etf_kline',
    'get_full_data',
    'generate_signals',
    'build_api_response',
    'get_gold_news',
    'build_news_response',
]
