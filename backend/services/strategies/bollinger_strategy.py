from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class BollingerStrategy(BaseStrategy):
    name = "bollinger"
    display_name = "布林带策略"
    description = "基于布林带均值回归，价格触下轨买入，触上轨卖出，中轨持有"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        bb_upper = float(latest.get("BB_UPPER", 0))
        bb_lower = float(latest.get("BB_LOWER", 0))
        bb_mid = float(latest.get("BB_MID", 0))
        close = float(latest["收盘"])

        if bb_upper <= 0 or bb_lower <= 0 or bb_mid <= 0:
            return {"signal": "观望", "position_ratio": 0.5, "action_desc": "布林带数据不足"}

        bb_width = (bb_upper - bb_lower) / bb_mid * 100
        price_pos = (close - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        price_pos = max(0.0, min(1.0, price_pos))

        if close <= bb_lower:
            signal = "买入"
            position_ratio = round(0.8 + 0.2 * (1 - price_pos), 4)
            action_desc = f"价格{close:.4f}触及布林下轨{bb_lower:.4f}，超卖买入"
        elif close >= bb_upper:
            signal = "卖出"
            position_ratio = round(0.1 + 0.1 * price_pos, 4)
            action_desc = f"价格{close:.4f}触及布林上轨{bb_upper:.4f}，超买卖出"
        elif close < bb_mid:
            signal = "持有"
            position_ratio = round(0.3 + 0.3 * price_pos, 4)
            action_desc = f"价格在中轨下方，偏多持有（位置{price_pos:.0%}）"
        else:
            signal = "持有"
            position_ratio = round(0.3 + 0.3 * price_pos, 4)
            action_desc = f"价格在中轨上方，偏空持有（位置{price_pos:.0%}）"

        return {
            "signal": signal,
            "position_ratio": position_ratio,
            "action_desc": action_desc,
            "base_price": bb_mid,
            "grid_info": {
                "bb_upper": round(bb_upper, 4),
                "bb_lower": round(bb_lower, 4),
                "bb_mid": round(bb_mid, 4),
                "bb_width_pct": round(bb_width, 2),
                "price_position": round(price_pos, 4),
            },
        }

    def get_config_schema(self) -> list:
        return [
            {"key": "grid_spread", "label": "布林带倍数", "type": "number", "default": 2, "min": 1, "max": 3, "step": 0.5},
        ]
