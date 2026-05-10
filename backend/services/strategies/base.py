from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd


class BaseStrategy(ABC):
    """策略基类，所有交易策略必须继承此类并实现 calc_signal 方法"""

    name: str = "base"
    display_name: str = "基础策略"
    description: str = ""

    @abstractmethod
    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        """
        计算交易信号

        Args:
            latest: 最新一行K线数据 (pandas Series)
            df: 完整K线数据 (pandas DataFrame)
            config: 任务配置字典

        Returns:
            dict: {
                "signal": "买入" | "卖出" | "持有" | "观望",
                "position_ratio": float (0.0-1.0),
                "action_desc": str,
                "base_price": float | None,
                "grid_info": dict | None,
            }
        """
        pass

    def get_config_schema(self) -> list:
        """
        返回该策略的配置项定义，供前端动态渲染

        Returns:
            list of dict: [
                {"key": "grid_count", "label": "网格数量", "type": "number", "default": 10, "min": 2, "max": 50},
                ...
            ]
        """
        return []
