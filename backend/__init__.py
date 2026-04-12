"""
backend 包：Flask 后端模块

本包采用分层架构：
- routes/    : API 路由（接收请求，调用 service，返回 JSON）
- services/  : 业务逻辑（数据获取、指标计算、信号生成）
- utils/     : 工具函数（技术指标计算）
- models/    : 数据模型（用户等）
"""

from backend.routes import data_bp, news_bp

__all__ = ['data_bp', 'news_bp']
