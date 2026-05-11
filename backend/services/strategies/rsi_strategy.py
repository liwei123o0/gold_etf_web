from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class RSIStrategy(BaseStrategy):
    name = "rsi"
    display_name = "RSI策略"
    description = "基于RSI超买超卖，RSI<30买入，RSI>70卖出，中间持有"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        rsi = float(latest.get("RSI", 50))
        close = float(latest["收盘"])
        oversold = config.get("rsi_oversold", 30)
        overbought = config.get("rsi_overbought", 70)

        if rsi <= oversold:
            signal = "买入"
            position_ratio = round(0.5 + 0.5 * (oversold - rsi) / oversold, 4)
            position_ratio = min(position_ratio, 1.0)
            action_desc = f"RSI={rsi:.1f} ≤ {oversold}，超卖买入"
        elif rsi >= overbought:
            signal = "卖出"
            position_ratio = round(0.3 * (100 - rsi) / (100 - overbought), 4)
            position_ratio = max(position_ratio, 0.05)
            action_desc = f"RSI={rsi:.1f} ≥ {overbought}，超买卖出"
        else:
            signal = "持有"
            mid = (oversold + overbought) / 2
            if rsi < mid:
                position_ratio = round(0.4 + 0.2 * (mid - rsi) / (mid - oversold), 4)
            else:
                position_ratio = round(0.4 + 0.2 * (overbought - rsi) / (overbought - mid), 4)
            action_desc = f"RSI={rsi:.1f}，中性持有"

        return {
            "signal": signal,
            "position_ratio": position_ratio,
            "action_desc": action_desc,
            "base_price": close,
            "grid_info": {
                "rsi": round(rsi, 2),
                "oversold_threshold": oversold,
                "overbought_threshold": overbought,
            },
        }

    def get_config_schema(self) -> list:
        return [
            {"key": "rsi_oversold", "label": "超卖阈值", "type": "number", "default": 30, "min": 10, "max": 40},
            {"key": "rsi_overbought", "label": "超买阈值", "type": "number", "default": 70, "min": 60, "max": 90},
        ]
