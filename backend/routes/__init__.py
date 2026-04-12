"""
backend.routes 包：API 路由
"""
from backend.routes.data import bp as data_bp
from backend.routes.news import bp as news_bp

__all__ = ['data_bp', 'news_bp']
