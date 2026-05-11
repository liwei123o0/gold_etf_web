from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class MACDCrossStrategy(BaseStrategy):
    name = "macd_cross"
    display_name = "MACD金叉死叉策略"
    description = "基于MACD金叉死叉，DIF上穿DEA买入，下穿卖出"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        close = float(latest["收盘"])
        dif = float(latest.get("MACD", 0))
        dea = float(latest.get("MACD_SIGNAL", 0))
        hist = float(latest.get("MACD_HIST", 0))

        if len(df) < 3:
            return {"signal": "观望", "position_ratio": 0.5, "action_desc": "数据不足"}

        prev_dif = float(df["MACD"].iloc[-2]) if "MACD" in df.columns else 0
        prev_dea = float(df["MACD_SIGNAL"].iloc[-2]) if "MACD_SIGNAL" in df.columns else 0

        golden_cross = prev_dif <= prev_dea and dif > dea
        death_cross = prev_dif >= prev_dea and dif < dea

        if golden_cross:
            signal = "买入"
            hist_strength = min(abs(hist) / max(abs(dif), 0.001), 1.0)
            position_ratio = round(0.6 + 0.4 * hist_strength, 4)
            action_desc = f"MACD金叉：DIF={dif:.4f}上穿DEA={dea:.4f}，买入"
        elif death_cross:
            signal = "卖出"
            position_ratio = 0.1
            action_desc = f"MACD死叉：DIF={dif:.4f}下穿DEA={dea:.4f}，卖出"
        elif dif > dea:
            signal = "持有"
            position_ratio = round(0.5 + 0.3 * min(hist / max(abs(dif), 0.001), 1.0), 4)
            action_desc = f"MACD多头：DIF={dif:.4f}>DEA={dea:.4f}，持有"
        else:
            signal = "持有"
            position_ratio = round(0.2 + 0.1 * max(hist / max(abs(dif), 0.001), -1.0), 4)
            action_desc = f"MACD空头：DIF={dif:.4f}<DEA={dea:.4f}，持有"

        return {
            "signal": signal,
            "position_ratio": position_ratio,
            "action_desc": action_desc,
            "base_price": close,
            "grid_info": {
                "dif": round(dif, 6),
                "dea": round(dea, 6),
                "hist": round(hist, 6),
                "golden_cross": golden_cross,
                "death_cross": death_cross,
            },
        }

    def get_config_schema(self) -> list:
        return []
