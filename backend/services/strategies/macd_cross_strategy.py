"""
MACD金叉死叉策略模块

基于MACD指标的DIF线与DEA线交叉关系生成交易信号：
- 金叉（DIF上穿DEA）：买入信号
- 死叉（DIF下穿DEA）：卖出信号
- 多头排列（DIF>DEA）：持有
- 空头排列（DIF<DEA）：持有但降低仓位
"""

from typing import Dict, Any
import pandas as pd
import logging

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class MACDCrossStrategy(BaseStrategy):
    """
    MACD金叉死叉策略

    通过MACD指标中DIF线与DEA线的交叉关系判断买卖时机：
    - 金叉（前一根DIF<=DEA，当前DIF>DEA）：趋势由空转多，发出买入信号
    - 死叉（前一根DIF>=DEA，当前DIF<DEA）：趋势由多转空，发出卖出信号
    - 多头排列（DIF>DEA但未发生金叉）：持有，仓位根据柱状图强度调整
    - 空头排列（DIF<DEA但未发生死叉）：持有，仓位较低

    仓位比例根据MACD柱状图（HIST）的强度动态调整，
    金叉时柱状图越强仓位越高，死叉时仓位降至最低。
    """

    name = "macd_cross"
    display_name = "MACD金叉死叉策略"
    description = "基于MACD金叉死叉，DIF上穿DEA买入，下穿卖出"

    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        """
        计算MACD金叉死叉交易信号

        从最新K线数据中提取MACD指标值（DIF、DEA、HIST），
        与前一根K线的指标值比较判断是否发生金叉或死叉，
        并根据柱状图强度计算建议仓位比例。

        Args:
            latest: 最新一行K线数据，需包含 MACD、MACD_SIGNAL、MACD_HIST 字段
            df: 完整K线历史数据，用于获取前一根K线的MACD值
            config: 任务配置字典（当前策略无额外配置项）

        Returns:
            dict: 交易信号字典，包含：
                - signal (str): 交易信号（买入/卖出/持有/观望）
                - position_ratio (float): 建议仓位比例
                - action_desc (str): 操作描述
                - base_price (float): 当前收盘价
                - grid_info (dict): MACD指标详情，包含 dif、dea、hist、golden_cross、death_cross
        """
        close = float(latest["收盘"])
        dif = float(latest.get("MACD", 0))
        dea = float(latest.get("MACD_SIGNAL", 0))
        hist = float(latest.get("MACD_HIST", 0))

        # 数据不足时返回观望信号
        if len(df) < 3:
            return {"signal": "观望", "position_ratio": 0.5, "action_desc": "数据不足"}

        # 获取前一根K线的DIF和DEA值，用于判断交叉
        prev_dif = float(df["MACD"].iloc[-2]) if "MACD" in df.columns else 0
        prev_dea = float(df["MACD_SIGNAL"].iloc[-2]) if "MACD_SIGNAL" in df.columns else 0

        # 判断金叉：前一根DIF<=DEA且当前DIF>DEA
        golden_cross = prev_dif <= prev_dea and dif > dea
        # 判断死叉：前一根DIF>=DEA且当前DIF<DEA
        death_cross = prev_dif >= prev_dea and dif < dea

        if golden_cross:
            # 金叉买入：仓位根据柱状图强度调整，范围0.6~1.0
            signal = "买入"
            hist_strength = min(abs(hist) / max(abs(dif), 0.001), 1.0)
            position_ratio = round(0.6 + 0.4 * hist_strength, 4)
            action_desc = f"MACD金叉：DIF={dif:.4f}上穿DEA={dea:.4f}，买入"
        elif death_cross:
            # 死叉卖出：仓位降至最低
            signal = "卖出"
            position_ratio = 0.1
            action_desc = f"MACD死叉：DIF={dif:.4f}下穿DEA={dea:.4f}，卖出"
        elif dif > dea:
            # 多头排列持有：仓位根据柱状图正向强度调整，范围0.5~0.8
            signal = "持有"
            position_ratio = round(0.5 + 0.3 * min(hist / max(abs(dif), 0.001), 1.0), 4)
            action_desc = f"MACD多头：DIF={dif:.4f}>DEA={dea:.4f}，持有"
        else:
            # 空头排列持有：仓位较低，范围0.1~0.3
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
        """
        返回MACD金叉死叉策略的配置项定义

        当前策略无额外配置项，返回空列表。

        Returns:
            list: 空列表
        """
        return []
