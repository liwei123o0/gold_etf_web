"""
策略工厂模块

提供策略注册、查找和列举功能。通过工厂模式统一管理所有策略实例，
支持按策略名称获取策略对象，以及动态注册新策略。
"""

from typing import Dict, Type, List, Dict as DictType

from .base import BaseStrategy
from .grid_strategy import GridStrategy
from .ma_trend_strategy import MATrendStrategy
from .bollinger_strategy import BollingerStrategy
from .rsi_strategy import RSIStrategy
from .macd_cross_strategy import MACDCrossStrategy


class StrategyFactory:
    """
    策略工厂类，负责策略的注册、查找和列举。

    使用类变量 _registry 维护策略名称到策略实例的映射，
    采用延迟加载方式（首次访问时初始化注册表）以避免循环导入。
    支持通过 get() 获取策略、register() 注册新策略、list_all() 列举所有策略。
    """

    _registry: DictType[str, BaseStrategy] = {}

    @classmethod
    def _ensure_loaded(cls):
        """
        确保策略注册表已加载。

        如果注册表为空，则初始化所有内置策略实例并注册。
        采用延迟加载机制，仅在首次调用时执行注册逻辑，
        避免模块导入时的循环依赖问题。
        """
        if not cls._registry:
            cls._registry = {
                "grid": GridStrategy(),
                "ma_trend": MATrendStrategy(),
                "bollinger": BollingerStrategy(),
                "rsi": RSIStrategy(),
                "macd_cross": MACDCrossStrategy(),
            }

    @classmethod
    def get(cls, strategy_name: str) -> BaseStrategy:
        """
        根据策略名称获取策略实例。

        Args:
            strategy_name: 策略的唯一标识名称，如 "grid"、"ma_trend" 等

        Returns:
            BaseStrategy: 对应名称的策略实例

        Raises:
            ValueError: 当策略名称不存在时抛出异常，提示可用策略列表
        """
        cls._ensure_loaded()
        strategy = cls._registry.get(strategy_name)
        if strategy is None:
            raise ValueError(f"未知策略: {strategy_name}, 可用策略: {list(cls._registry.keys())}")
        return strategy

    @classmethod
    def register(cls, strategy: BaseStrategy):
        """
        注册新的策略实例到工厂。

        将策略实例按其 name 属性注册到注册表中，
        支持运行时动态添加新策略。

        Args:
            strategy: 需要注册的策略实例，必须为 BaseStrategy 的子类实例
        """
        cls._registry[strategy.name] = strategy

    @classmethod
    def list_all(cls) -> List[DictType]:
        """
        列举所有已注册策略的元信息。

        返回每个策略的名称、显示名称、描述和配置项定义，
        供前端渲染策略选择列表和配置表单。

        Returns:
            list[dict]: 策略元信息列表，每个元素包含：
                - name (str): 策略唯一标识
                - display_name (str): 中文显示名称
                - description (str): 策略功能描述
                - config_schema (list): 配置项定义列表
        """
        cls._ensure_loaded()
        return [
            {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "config_schema": s.get_config_schema(),
            }
            for s in cls._registry.values()
        ]
