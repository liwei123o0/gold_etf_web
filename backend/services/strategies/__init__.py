"""
策略包初始化模块

统一导出所有策略类和策略工厂，方便外部模块通过
from backend.services.strategies import xxx 的方式导入使用。
"""

from .base import BaseStrategy
from .grid_strategy import GridStrategy
from .ma_trend_strategy import MATrendStrategy
from .bollinger_strategy import BollingerStrategy
from .rsi_strategy import RSIStrategy
from .macd_cross_strategy import MACDCrossStrategy
from .factory import StrategyFactory

__all__ = [
    "BaseStrategy", "GridStrategy", "MATrendStrategy",
    "BollingerStrategy", "RSIStrategy", "MACDCrossStrategy",
    "StrategyFactory",
]
