from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy
from backend.services import grid_trade

logger = logging.getLogger(__name__)


class GridStrategy(BaseStrategy):
    name = "grid"
    display_name = "网格策略"
    description = "基于均线基准价构建网格，在网格上下界之间低买高卖"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        grid_count = config.get("grid_count", 10)
        grid_spread = config.get("grid_spread", 0.10)
        base_ma_key = config.get("base_ma_key", "MA20")
        macd_ma_key = config.get("macd_ma_key")

        macd_hist_mean = None
        if macd_ma_key:
            window = 20
            macd_hist_mean = df["MACD_HIST"].iloc[-window:].mean() if len(df) >= window else df["MACD_HIST"].mean()

        return grid_trade.get_grid_signal(
            latest,
            grid_count=grid_count,
            grid_spread=grid_spread,
            ma_key=base_ma_key,
            macd_ma_key=macd_ma_key,
            macd_hist_mean=macd_hist_mean,
        )

    def get_config_schema(self) -> list:
        return [
            {"key": "grid_count", "label": "网格数量", "type": "number", "default": 10, "min": 2, "max": 50},
            {"key": "grid_spread", "label": "网格间距(%)", "type": "number", "default": 10, "min": 1, "max": 50, "step": 0.5},
            {"key": "base_ma_key", "label": "基准均线", "type": "select", "default": "MA20", "options": ["MA5", "MA10", "MA20", "MA60"]},
            {"key": "macd_ma_key", "label": "MACD指标", "type": "select", "default": "", "options": ["", "MACD_DIF", "MACD_SIGNAL"]},
        ]
