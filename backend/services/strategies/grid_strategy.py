"""
网格策略模块

基于均线基准价构建网格交易策略，在网格上下界之间低买高卖。
核心逻辑委托给 grid_trade 服务模块的 get_grid_signal 函数实现。
"""

from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy
from backend.services import grid_trade

logger = logging.getLogger(__name__)


class GridStrategy(BaseStrategy):
    """
    网格交易策略

    以指定均线（默认MA20）为基准价，按设定的网格数量和间距构建价格网格，
    在网格线之间执行低买高卖操作。可选配合 MACD 指标进行信号过滤，
    当 MACD 柱状均值偏向多头时增强买入信号，偏向空头时增强卖出信号。
    """

    name = "grid"
    display_name = "网格策略"
    description = "基于均线基准价构建网格，在网格上下界之间低买高卖"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        """
        计算网格交易信号

        从配置中提取网格参数和均线参数，若启用了 MACD 辅助指标，
        则计算 MACD 柱状图的均值用于信号增强，最终委托
        grid_trade.get_grid_signal 函数生成交易信号。

        Args:
            latest: 最新一行K线数据
            df: 完整K线历史数据
            config: 任务配置字典，支持以下参数：
                - grid_count (int): 网格数量，默认 10
                - grid_spread (float): 网格间距百分比，默认 0.10（即10%）
                - base_ma_key (str): 基准均线字段名，默认 "MA20"
                - macd_ma_key (str): MACD辅助指标字段名，默认为空（不启用）

        Returns:
            dict: 交易信号字典，包含 signal、position_ratio、action_desc、
                  base_price、grid_info 等字段
        """
        grid_count = config.get("grid_count", 10)
        grid_spread = config.get("grid_spread", 0.10)
        base_ma_key = config.get("base_ma_key", "MA20")
        macd_ma_key = config.get("macd_ma_key")

        macd_hist_mean = None
        if macd_ma_key:
            window = 20
            # 计算最近20根K线的MACD柱状图均值，数据不足时使用全部数据
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
        """
        返回网格策略的配置项定义

        配置项包括：
        - grid_count: 网格数量（2~50）
        - grid_spread: 网格间距百分比（1%~50%）
        - base_ma_key: 基准均线选择（MA5/MA10/MA20/MA60）
        - macd_ma_key: MACD辅助指标选择（不使用/MACD_DIF/MACD_SIGNAL）

        Returns:
            list[dict]: 配置项定义列表
        """
        return [
            {"key": "grid_count", "label": "网格数量", "type": "number", "default": 10, "min": 2, "max": 50},
            {"key": "grid_spread", "label": "网格间距(%)", "type": "number", "default": 10, "min": 1, "max": 50, "step": 0.5},
            {"key": "base_ma_key", "label": "基准均线", "type": "select", "default": "MA20", "options": ["MA5", "MA10", "MA20", "MA60"]},
            {"key": "macd_ma_key", "label": "MACD指标", "type": "select", "default": "", "options": ["", "MACD_DIF", "MACD_SIGNAL"]},
        ]
