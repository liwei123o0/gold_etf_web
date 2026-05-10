from typing import Dict, Any
import pandas as pd

from .base import BaseStrategy
from backend.services import grid_trade


class MATrendStrategy(BaseStrategy):
    name = "ma_trend"
    display_name = "MA趋势策略"
    description = "基于快慢均线金叉死叉判断趋势方向，顺势交易"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        fast_ma_key = config.get("base_ma_key", "MA5")
        slow_ma_key = config.get("trend_ma_key", "MA20")
        position_size = config.get("position_size", 1.0)

        return grid_trade.get_ma_trend_signal(
            latest,
            fast_ma_key=fast_ma_key,
            slow_ma_key=slow_ma_key,
            position_size=position_size,
        )

    def get_config_schema(self) -> list:
        return [
            {"key": "base_ma_key", "label": "快线均线", "type": "select", "default": "MA5", "options": ["MA5", "MA10", "MA20"]},
            {"key": "trend_ma_key", "label": "慢线均线", "type": "select", "default": "MA20", "options": ["MA10", "MA20", "MA60"]},
        ]
