"""
策略基类模块

定义所有交易策略的抽象基类 BaseStrategy，所有具体策略必须继承此类
并实现 calc_signal 方法。该模块是整个策略体系的核心接口规范。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd


class BaseStrategy(ABC):
    """
    策略基类，所有交易策略必须继承此类并实现 calc_signal 方法。

    该类定义了策略的公共属性和接口规范：
    - name: 策略的唯一标识名称，用于工厂注册和查找
    - display_name: 策略的中文显示名称，供前端展示
    - description: 策略的功能描述，供前端展示
    - calc_signal: 抽象方法，子类必须实现，用于计算交易信号
    - get_config_schema: 返回策略配置项定义，供前端动态渲染配置表单
    """

    name: str = "base"
    display_name: str = "基础策略"
    description: str = ""

    @abstractmethod
    def calc_signal(self, latest: pd.Series, df: pd.DataFrame, config: dict) -> Dict[str, Any]:
        """
        计算交易信号（抽象方法，子类必须实现）

        根据最新K线数据和历史K线数据，结合任务配置，计算当前应执行的操作信号。

        Args:
            latest: 最新一行K线数据，pandas Series 对象，包含收盘价、均线、指标等字段
            df: 完整K线历史数据，pandas DataFrame 对象，用于回溯计算
            config: 任务配置字典，包含该策略的参数配置（如网格数量、阈值等）

        Returns:
            dict: 交易信号字典，包含以下字段：
                - signal (str): 交易信号，取值为 "买入" | "卖出" | "持有" | "观望"
                - position_ratio (float): 建议仓位比例，范围 0.0 ~ 1.0
                - action_desc (str): 操作描述文本，用于前端展示
                - base_price (float | None): 基准价格（如均线价格、布林中轨等）
                - grid_info (dict | None): 策略附加信息（如指标数值、网格参数等）
        """
        pass

    def get_config_schema(self) -> list:
        """
        返回该策略的配置项定义，供前端动态渲染配置表单。

        每个配置项为一个字典，包含 key（字段名）、label（显示标签）、
        type（控件类型）、default（默认值）等字段。

        Returns:
            list[dict]: 配置项定义列表，每个元素格式如下：
                {
                    "key": "grid_count",        # 配置项字段名
                    "label": "网格数量",         # 前端显示标签
                    "type": "number",           # 控件类型: number / select
                    "default": 10,              # 默认值
                    "min": 2,                   # 最小值（number 类型）
                    "max": 50,                  # 最大值（number 类型）
                    "options": [...]            # 可选项（select 类型）
                }
        """
        return []
