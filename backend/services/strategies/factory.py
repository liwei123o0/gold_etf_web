from typing import Dict, Type, List, Dict as DictType

from .base import BaseStrategy
from .grid_strategy import GridStrategy
from .ma_trend_strategy import MATrendStrategy
from .bollinger_strategy import BollingerStrategy
from .rsi_strategy import RSIStrategy
from .macd_cross_strategy import MACDCrossStrategy


class StrategyFactory:
    _registry: DictType[str, BaseStrategy] = {}

    @classmethod
    def _ensure_loaded(cls):
        if not cls._registry:
            cls._registry = {
                "grid": GridStrategy(),
                "ma_trend": MATrendStrategy(),
                "bollinger": BollingerStrategy(),
                "rsi": RSIStrategy(),
                "macd_cross": MACDCrossStrategy(),
            }

    @classmethod
    def get(cls, strategy_name: str) -> BaseStrategy:
        cls._ensure_loaded()
        strategy = cls._registry.get(strategy_name)
        if strategy is None:
            raise ValueError(f"未知策略: {strategy_name}, 可用策略: {list(cls._registry.keys())}")
        return strategy

    @classmethod
    def register(cls, strategy: BaseStrategy):
        cls._registry[strategy.name] = strategy

    @classmethod
    def list_all(cls) -> List[DictType]:
        cls._ensure_loaded()
        return [
            {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "config_schema": s.get_config_schema(),
            }
            for s in cls._registry.values()
        ]
