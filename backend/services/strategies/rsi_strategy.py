"""
RSI策略模块

基于RSI（相对强弱指标）的超买超卖区间生成交易信号：
- RSI低于超卖阈值（默认30）：超卖买入
- RSI高于超买阈值（默认70）：超买卖出
- RSI处于中间区间：中性持有
"""

from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class RSIStrategy(BaseStrategy):
    """
    RSI超买超卖策略

    通过RSI指标判断市场的超买超卖状态：
    - RSI <= 超卖阈值（默认30）：市场超卖，发出买入信号，RSI越低仓位越高
    - RSI >= 超买阈值（默认70）：市场超买，发出卖出信号，RSI越高仓位越低
    - RSI处于中间区间：中性持有，仓位根据RSI与中值的关系调整

    超卖和超买阈值可通过配置参数自定义调整。
    """

    name = "rsi"
    display_name = "RSI策略"
    description = "基于RSI超买超卖，RSI<30买入，RSI>70卖出，中间持有"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        """
        计算RSI超买超卖交易信号

        从最新K线数据中提取RSI值，与配置的超买超卖阈值比较，
        生成对应的交易信号和仓位建议。

        Args:
            latest: 最新一行K线数据，需包含 RSI 字段
            df: 完整K线历史数据
            config: 任务配置字典，支持以下参数：
                - rsi_oversold (int): 超卖阈值，默认 30
                - rsi_overbought (int): 超买阈值，默认 70

        Returns:
            dict: 交易信号字典，包含：
                - signal (str): 交易信号（买入/卖出/持有）
                - position_ratio (float): 建议仓位比例
                - action_desc (str): 操作描述
                - base_price (float): 当前收盘价
                - grid_info (dict): RSI指标详情，包含 rsi、oversold_threshold、overbought_threshold
        """
        rsi = float(latest.get("RSI", 50))
        close = float(latest["收盘"])
        oversold = config.get("rsi_oversold", 30)
        overbought = config.get("rsi_overbought", 70)

        if rsi <= oversold:
            # 超卖区间：RSI越低买入信号越强，仓位范围0.5~1.0
            signal = "买入"
            position_ratio = round(0.5 + 0.5 * (oversold - rsi) / oversold, 4)
            position_ratio = min(position_ratio, 1.0)
            action_desc = f"RSI={rsi:.1f} ≤ {oversold}，超卖买入"
        elif rsi >= overbought:
            # 超买区间：RSI越高卖出信号越强，仓位范围0.05~0.3
            signal = "卖出"
            position_ratio = round(0.3 * (100 - rsi) / (100 - overbought), 4)
            position_ratio = max(position_ratio, 0.05)
            action_desc = f"RSI={rsi:.1f} ≥ {overbought}，超买卖出"
        else:
            # 中性区间：仓位根据RSI与超买超卖中值的关系调整，范围0.4~0.6
            signal = "持有"
            mid = (oversold + overbought) / 2
            if rsi < mid:
                # RSI低于中值，偏多持有
                position_ratio = round(0.4 + 0.2 * (mid - rsi) / (mid - oversold), 4)
            else:
                # RSI高于中值，偏空持有
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
        """
        返回RSI策略的配置项定义

        配置项包括：
        - rsi_oversold: 超卖阈值（10~40），默认30
        - rsi_overbought: 超买阈值（60~90），默认70

        Returns:
            list[dict]: 配置项定义列表
        """
        return [
            {"key": "rsi_oversold", "label": "超卖阈值", "type": "number", "default": 30, "min": 10, "max": 40},
            {"key": "rsi_overbought", "label": "超买阈值", "type": "number", "default": 70, "min": 60, "max": 90},
        ]
