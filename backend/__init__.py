"""
backend 包：后端模块（FastAPI 重构版）

本包采用分层架构：
- routes/    : API 路由（函数形式，供 FastAPI 直接调用）
- services/  : 业务逻辑（数据获取、指标计算、信号生成）
- utils/     : 工具函数（技术指标计算）
- models/    : 数据模型 + Pydantic schemas
- core/      : 核心工具（JWT、security）
"""

__all__ = []  # FastAPI 不再从包级别导入 blueprint