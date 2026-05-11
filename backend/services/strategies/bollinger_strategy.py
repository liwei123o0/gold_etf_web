"""
布林带策略模块

基于布林带（Bollinger Bands）的均值回归策略：
- 价格触及下轨：超卖买入
- 价格触及上轨：超买卖出
- 价格在中轨附近：根据位置偏多或偏空持有
"""

from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class BollingerStrategy(BaseStrategy):
    """
    布林带均值回归策略

    利用布林带的上轨、中轨、下轨判断价格偏离程度：
    - 价格 <= 下轨：超卖区域，发出买入信号，仓位较高（0.8~1.0）
    - 价格 >= 上轨：超买区域，发出卖出信号，仓位较低（0.1~0.2）
    - 价格 < 中轨：偏多持有，仓位根据价格在布林带中的位置调整
    - 价格 >= 中轨：偏空持有，仓位根据价格在布林带中的位置调整

    价格位置（price_position）= (收盘价 - 下轨) / (上轨 - 下轨)，
    取值范围 0~1，0表示在下轨，1表示在上轨。
    """

    name = "bollinger"
    display_name = "布林带策略"
    description = "基于布林带均值回归，价格触下轨买入，触上轨卖出，中轨持有"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        """
        计算布林带均值回归交易信号

        从最新K线数据中提取布林带上轨、中轨、下轨值，
        计算价格在布林带中的位置百分比，据此生成交易信号。

        Args:
            latest: 最新一行K线数据，需包含 BB_UPPER、BB_LOWER、BB_MID 字段
            df: 完整K线历史数据
            config: 任务配置字典，支持以下参数：
                - grid_spread (float): 布林带倍数，默认 2

        Returns:
            dict: 交易信号字典，包含：
                - signal (str): 交易信号（买入/卖出/持有/观望）
                - position_ratio (float): 建议仓位比例
                - action_desc (str): 操作描述
                - base_price (float): 布林带中轨价格
                - grid_info (dict): 布林带指标详情，包含 bb_upper、bb_lower、bb_mid、bb_width_pct、price_position
        """
        bb_upper = float(latest.get("BB_UPPER", 0))
        bb_lower = float(latest.get("BB_LOWER", 0))
        bb_mid = float(latest.get("BB_MID", 0))
        close = float(latest["收盘"])

        # 布林带数据无效时返回观望信号
        if bb_upper <= 0 or bb_lower <= 0 or bb_mid <= 0:
            return {"signal": "观望", "position_ratio": 0.5, "action_desc": "布林带数据不足"}

        # 计算布林带宽度百分比（上轨-下轨）/中轨*100
        bb_width = (bb_upper - bb_lower) / bb_mid * 100
        # 计算价格在布林带中的位置：0=下轨，1=上轨
        price_pos = (close - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        price_pos = max(0.0, min(1.0, price_pos))

        if close <= bb_lower:
            # 触及下轨：超卖买入，仓位0.8~1.0
            signal = "买入"
            position_ratio = round(0.8 + 0.2 * (1 - price_pos), 4)
            action_desc = f"价格{close:.4f}触及布林下轨{bb_lower:.4f}，超卖买入"
        elif close >= bb_upper:
            # 触及上轨：超买卖出，仓位0.1~0.2
            signal = "卖出"
            position_ratio = round(0.1 + 0.1 * price_pos, 4)
            action_desc = f"价格{close:.4f}触及布林上轨{bb_upper:.4f}，超买卖出"
        elif close < bb_mid:
            # 中轨下方：偏多持有，仓位0.3~0.6
            signal = "持有"
            position_ratio = round(0.3 + 0.3 * price_pos, 4)
            action_desc = f"价格在中轨下方，偏多持有（位置{price_pos:.0%}）"
        else:
            # 中轨上方：偏空持有，仓位0.3~0.6
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
        """
        返回布林带策略的配置项定义

        配置项包括：
        - grid_spread: 布林带倍数（1~3），默认2

        Returns:
            list[dict]: 配置项定义列表
        """
        return [
            {"key": "grid_spread", "label": "布林带倍数", "type": "number", "default": 2, "min": 1, "max": 3, "step": 0.5},
        ]
