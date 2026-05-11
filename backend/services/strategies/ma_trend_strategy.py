"""
均线趋势策略模块

基于快慢均线的金叉死叉判断趋势方向，顺势交易。
核心逻辑委托给 grid_trade 服务模块的 get_ma_trend_signal 函数实现。
"""

from typing import Dict, Any
import pandas as pd

from .base import BaseStrategy
from backend.services import grid_trade


class MATrendStrategy(BaseStrategy):
    """
    均线趋势策略

    通过快线（短期均线）和慢线（长期均线）的交叉关系判断趋势方向：
    - 金叉（快线上穿慢线）：趋势转多，发出买入信号
    - 死叉（快线下穿慢线）：趋势转空，发出卖出信号
    - 其他情况：根据价格与均线的位置关系，持有或观望

    默认使用 MA5（快线）和 MA20（慢线）组合。
    """

    name = "ma_trend"
    display_name = "MA趋势策略"
    description = "基于快慢均线金叉死叉判断趋势方向，顺势交易"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        """
        计算均线趋势交易信号

        从配置中提取快慢均线参数和仓位比例，委托
        grid_trade.get_ma_trend_signal 函数生成交易信号。

        Args:
            latest: 最新一行K线数据
            df: 完整K线历史数据
            config: 任务配置字典，支持以下参数：
                - base_ma_key (str): 快线均线字段名，默认 "MA5"
                - trend_ma_key (str): 慢线均线字段名，默认 "MA20"
                - position_size (float): 仓位比例，默认 1.0

        Returns:
            dict: 交易信号字典，包含 signal、position_ratio、action_desc、
                  base_price、grid_info 等字段
        """
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
        """
        返回均线趋势策略的配置项定义

        配置项包括：
        - base_ma_key: 快线均线选择（MA5/MA10/MA20）
        - trend_ma_key: 慢线均线选择（MA10/MA20/MA60）

        Returns:
            list[dict]: 配置项定义列表
        """
        return [
            {"key": "base_ma_key", "label": "快线均线", "type": "select", "default": "MA5", "options": ["MA5", "MA10", "MA20"]},
            {"key": "trend_ma_key", "label": "慢线均线", "type": "select", "default": "MA20", "options": ["MA10", "MA20", "MA60"]},
        ]
