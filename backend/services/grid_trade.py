"""
网格交易计算服务

提供网格交易的参数计算、信号生成、模拟回测功能。
适用于震荡市场的低买高卖策略。

支持两类基准锚定模式：
- 均线基准（MA）：以 MA5/MA10/MA20/MA60 作为网格基准价
- MACD基准：以 MACD 指标（DIF/DEA）结合 MACD_HIST 趋势强度动态调整网格

MACD 网格模式说明：
- macd_ma_key='MACD'       → 以 DIF（EMA12-EMA26）作为基准值，结合 HIST 调整网格
- macd_ma_key='MACD_SIGNAL' → 以 DEA（MACD的9日EMA）作为基准值
- MACD_HIST 历史均值大（趋势强）→ 自动扩大网格区间
- MACD_HIST 历史均值小（震荡） → 自动缩小网格区间
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
import logging


# ==================== 全局常量配置 ====================

logger = logging.getLogger(__name__)

# 默认网格格数（将价格区间划分为 N 个网格档位）
DEFAULT_GRID_COUNT = 10

# 默认网格区间总幅度（上下10%，即基准价 ±5%）
DEFAULT_GRID_SPREAD = 0.10

# 默认基准价在网格区间的位置（0.5 表示基准价位于网格正中间）
DEFAULT_BASE_RATIO = 0.50

# 有效的 MACD 基准类型（用于参数校验）
VALID_MACD_MA_KEYS = ('MACD', 'MACD_SIGNAL')

# MACD 基准模式下，HIST 均值对网格系数的映射配置
# key: MACD_HIST N日均值绝对值的分档阈值（单位：与价格同一量纲）
# value: spread 乘数（>1 扩大网格区间，<1 缩小网格区间）
_MACD_HIST_SPREAD_FACTOR = {
    (0.000, 0.002): 0.80,   # 震荡市场：HIST 均值小，缩小网格以降低交易成本
    (0.002, 0.005): 1.00,  # 正常市场：保持默认网格宽度
    (0.005, 0.010): 1.20,  # 趋势偏强：适当扩大网格，避免频繁触发
    (0.010, float('inf')): 1.50,  # 强趋势：大幅扩大网格，减少无效交易
}


def calc_grid_params(close: float,
                     grid_count: int = DEFAULT_GRID_COUNT,
                     grid_spread: float = DEFAULT_GRID_SPREAD,
                     base_ratio: float = DEFAULT_BASE_RATIO) -> Dict[str, Any]:
    """
    计算网格交易的基础参数。

    根据当前价格和网格配置，计算网格的上下边界、各档位价格、
    当前价格所在格位等核心参数。

    Parameters
    ----------
    close : float
        当前收盘价，作为网格基准价
    grid_count : int, optional
        网格格数，默认为 10 格（格数越多，交易频率越高，单次收益越小）
    grid_spread : float, optional
        网格总幅度，默认为 0.10（即上下各 5%，总区间 10%）
    base_ratio : float, optional
        基准价在网格区间的位置比例，默认为 0.5（正中间）
        - 0.0 表示基准价在网格最底部
        - 1.0 表示基准价在网格最顶部
        - 0.5 表示基准价在网格正中间

    Returns
    -------
    Dict[str, Any]
        网格参数字典，包含以下字段：
        - base_price: 基准价
        - grid_prices: 各档位价格列表（从低到高）
        - step_size: 每格价格步长
        - step_pct: 每格价格步长百分比
        - lower_bound: 网格下边界价格
        - upper_bound: 网格上边界价格
        - grid_spread_pct: 网格总幅度百分比
        - current_index: 当前价格所在格序号
        - grid_count: 网格总格数
        - grid_from_bottom: 距离网格底部的格数
        - grid_from_top: 距离网格顶部的格数
        - grid_returns: 各格收益率列表
        - base_index: 基准价所在格序号
    """
    # 计算网格上下边界（以基准价为中心，上下各 spread/2）
    half = grid_spread / 2
    lower_price = close * (1 - half)  # 网格下边界
    upper_price = close * (1 + half)  # 网格上边界

    # 使用等差数列生成各格价格（从低到高排列）
    grid_prices = np.linspace(lower_price, upper_price, grid_count + 1)
    step_size = grid_prices[1] - grid_prices[0]  # 每格价格差

    # 基准价在网格中的位置索引
    base_price = close
    base_index = np.searchsorted(grid_prices, base_price)
    base_index = min(max(base_index, 0), grid_count)  # 边界保护

    # 当前价格在网格中的格序（0=最低格，grid_count=最高格）
    current_index = np.searchsorted(grid_prices, close)
    current_index = min(max(current_index, 0), grid_count)  # 边界保护

    # 计算每格收益率（买入该格下限，卖出该格上限的收益率）
    grid_returns = []
    for i in range(len(grid_prices) - 1):
        ret = (grid_prices[i + 1] - grid_prices[i]) / grid_prices[i] * 100
        grid_returns.append(ret)

    # 距离上下边界的格数（用于判断是否接近网格边缘）
    grid_from_bottom = current_index
    grid_from_top = grid_count - current_index

    return {
        'base_price': base_price,
        'grid_prices': grid_prices.tolist(),
        'step_size': step_size,
        'step_pct': step_size / close * 100,
        'lower_bound': lower_price,
        'upper_bound': upper_price,
        'grid_spread_pct': grid_spread * 100,
        'current_index': current_index,
        'grid_count': grid_count,
        'grid_from_bottom': grid_from_bottom,
        'grid_from_top': grid_from_top,
        'grid_returns': grid_returns,
        'base_index': base_index,
    }


def calc_grid_position(close: float, grid_prices: List[float]) -> Dict[str, Any]:
    """
    根据当前价格计算持仓建议。

    分析当前价格在网格中的位置，给出买入/卖出/持有的操作建议，
    以及建议的持仓比例。

    Parameters
    ----------
    close : float
        当前价格
    grid_prices : List[float]
        网格各档位价格列表（从低到高排列）

    Returns
    -------
    Dict[str, Any]
        持仓建议字典，包含以下字段：
        - action: 操作建议（"买入"/"卖出"/"持有"）
        - action_desc: 操作描述说明
        - current_price: 当前价格
        - current_grid: 当前所在格序号
        - total_grids: 网格总格数
        - position_ratio: 建议持仓比例（0.0~1.0）
        - position_pct: 当前格位百分比
        - nearby_lower: 相邻下格价格
        - nearby_upper: 相邻上格价格
    """
    n = len(grid_prices) - 1  # 格数（价格档位数 - 1）
    idx = np.searchsorted(grid_prices, close)  # 当前价格所在格序
    idx = min(max(idx, 0), n)  # 边界保护

    # 获取当前格的上下相邻价格
    lower = grid_prices[max(idx - 1, 0)]
    upper = grid_prices[min(idx + 1, n)]

    # 当前格距离网格底部的百分比（0%=最低格，100%=最高格）
    position_pct = idx / n * 100

    # 根据价格位置判断操作建议
    if idx == 0:
        # 价格触及网格底部，建议买入建仓
        action = "买入"
        action_desc = "价格触及网格底部，建议买入建仓"
    elif idx == n:
        # 价格触及网格顶部，建议止盈卖出
        action = "卖出"
        action_desc = "价格触及网格顶部，建议止盈卖出"
    elif close <= lower:
        # 价格跌破当前格下限，触发买入信号
        action = "买入"
        action_desc = f"价格跌破格{int(idx-1)}线，建议买入"
    elif close >= upper:
        # 价格升破当前格上限，触发卖出信号
        action = "卖出"
        action_desc = f"价格升破格{int(idx+1)}线，建议卖出"
    else:
        # 价格在网格中间区域，持有观望
        action = "持有"
        action_desc = "价格在网格中位，持有观望"

    # 建议持仓比例（线性计算：底部100%，顶部0%）
    # 价格越低持仓越高，价格越高持仓越低
    position_ratio = (n - idx) / n

    return {
        'action': action,
        'action_desc': action_desc,
        'current_price': close,
        'current_grid': idx,
        'total_grids': n,
        'position_ratio': position_ratio,
        'position_pct': position_pct,
        'nearby_lower': grid_prices[max(idx - 1, 0)] if idx > 0 else None,
        'nearby_upper': grid_prices[min(idx + 1, n)] if idx < n else None,
    }


def _get_hist_spread_factor(hist_mean_abs: float) -> float:
    """
    根据 MACD_HIST 历史均值绝对值返回网格区间调整系数。

    MACD_HIST 反映趋势强度：
    - HIST 均值大 → 趋势强 → 扩大网格区间（避免频繁交易）
    - HIST 均值小 → 震荡市 → 缩小网格区间（降低交易成本）

    Parameters
    ----------
    hist_mean_abs : float
        MACD_HIST 的 N 日均值（取绝对值）

    Returns
    -------
    float
        spread 乘数系数（范围 0.8 ~ 1.5）
        - < 1.0：缩小网格区间
        - = 1.0：保持默认
        - > 1.0：扩大网格区间
    """
    # 遍历配置表，找到对应的系数
    for (low, high), factor in _MACD_HIST_SPREAD_FACTOR.items():
        if low <= hist_mean_abs < high:
            return factor
    return 1.0  # 默认不调整


def get_grid_signal(latest: pd.Series,
                    grid_count: int = DEFAULT_GRID_COUNT,
                    grid_spread: float = None,
                    ma_key: str = 'MA20',
                    macd_ma_key: str = None,
                    macd_hist_window: int = 20,
                    macd_hist_mean: float = None) -> Dict[str, Any]:
    """
    生成网格交易信号（支持均线锚定或 MACD 锚定两种模式）。

    ====================
    模式一：均线锚定模式（ma_key 指定均线，默认 MA20）
    ====================
    - 基准价 = 选定均线值（非当日收盘价）
      → 锚定市场平均成本，避免基准价随每日收盘价飘移
    - 区间 = 均线 ± 2×ATR（约覆盖 ±2ATR 的价格波动范围）
    - 持仓比例 = 1 - (当前价 - 下界) / 区间总宽度
      → 价格跌破均线越多，持仓越高（逢低加仓）
      → 价格涨超均线越多，持仓越低（逢高减仓）

    ====================
    模式二：MACD 锚定模式（macd_ma_key 指定 MACD 指标类型）
    ====================
    - 基准价 = 当前 MACD/DIF 值或 MACD_SIGNAL/DEA 值
      → 以 MACD 指标值本身作为网格基准（价格量纲相同）
    - 区间宽度根据 MACD_HIST 的历史均值动态调整：
      * HIST 均值大（趋势强）→ spread × 系数扩大网格（避免频繁触发）
      * HIST 均值小（震荡） → spread × 系数缩小网格（降低成本）
    - 持仓比例计算逻辑同均线锚定模式

    Parameters
    ----------
    latest : pd.Series
        最新行情数据，需包含以下字段：
        - 收盘：收盘价
        - MA5/MA10/MA20/MA60：各周期均线值
        - ATR：平均真实波幅
        - MACD/MACD_SIGNAL/MACD_HIST：MACD 指标值
    grid_count : int, optional
        网格格数，默认为 10 格
    grid_spread : float, optional
        手动指定网格总幅度。不指定时：
        - MA 模式：自动根据 ATR 计算（限制在 5%~30%）
        - MACD 模式：使用 DEFAULT_GRID_SPREAD × HIST 系数
    ma_key : str, optional
        基准均线字段名，默认为 'MA20'
        可选值：'MA5'、'MA10'、'MA20'、'MA60'
        仅在 macd_ma_key 未指定时生效
    macd_ma_key : str, optional
        MACD 基准类型，传入后切换到 MACD 锚定模式
        可选值：'MACD'（DIF 线）、'MACD_SIGNAL'（DEA 线）
    macd_hist_window : int, optional
        计算 MACD_HIST 历史均值的窗口天数，默认为 20 天
    macd_hist_mean : float, optional
        MACD_HIST 的历史均值（由调用方从完整数据列计算后传入）
        MACD 锚定模式下必须传入，否则 spread 系数默认 1.0

    Returns
    -------
    Dict[str, Any]
        网格信号字典，包含以下字段：
        - signal_name: 信号名称
        - signal: 操作信号（"买入"/"卖出"/"持有"/"观望"）
        - signal_text: 信号文本描述
        - close: 当前收盘价
        - ma_key: 使用的均线或 MACD 类型
        - ma_val: 基准价
        - ma_deviation_pct: 价格偏离基准百分比
        - base_price: 基准价
        - base_label: 基准标签
        - atr: ATR 值
        - atr_pct: ATR 占价格百分比
        - dynamic_spread: 是否动态计算区间
        - grid_count: 网格格数
        - grid_spread_pct: 网格总幅度百分比
        - step_pct: 每格步长百分比
        - lower_bound: 网格下边界
        - upper_bound: 网格上边界
        - current_grid: 当前所在格位
        - total_grids: 总格数
        - position_ratio: 建议持仓比例
        - nearby_lower: 相邻下格价格
        - nearby_upper: 相邻上格价格
        - action_desc: 操作描述

        MACD 锚定模式额外字段：
        - macd_ma_key: 使用的 MACD 均值类型
        - macd_hist_mean: MACD_HIST 的历史均值
        - macd_hist_current: 当前 MACD_HIST 值
        - grid_adjusted: 是否因 MACD 趋势调整了网格参数
    """
    close = float(latest['收盘'])

    # ========== 判断使用哪种基准模式 ==========
    use_macd_mode = macd_ma_key in VALID_MACD_MA_KEYS

    if use_macd_mode:
        # ==================== MACD 锚定模式 ====================
        # 获取 MACD 相关指标值
        macd_val = float(latest.get(macd_ma_key, 0))  # MACD 或 SIGNAL 值
        hist_current = float(latest.get('MACD_HIST', 0))  # 当前 HIST 值

        # MACD_HIST 历史均值由调用方计算后传入
        hist_mean = macd_hist_mean
        if macd_hist_mean is not None:
            hist_mean_abs = abs(macd_hist_mean)  # 取绝对值用于判断趋势强度
        else:
            hist_mean_abs = 0.0

        # 基准价设置（MACD 模式下使用收盘价作为基准）
        base_price = close
        base_label = f"收盘价={close:.4f}"

        # ATR 动态区间计算（MACD 模式也用 ATR 做基础 spread）
        atr = float(latest.get('ATR', 0))
        if atr <= 0 or grid_spread is not None:
            # ATR 无效或手动指定了 spread，使用默认值或指定值
            spread_base = grid_spread if grid_spread is not None else DEFAULT_GRID_SPREAD
            dynamic_spread = False
        else:
            # 根据 ATR 动态计算 spread（4 倍 ATR 覆盖约 95% 价格波动）
            spread_base = (4 * atr) / base_price if base_price != 0 else DEFAULT_GRID_SPREAD
            spread_base = max(0.05, min(0.30, spread_base))  # 限制在 5%~30%
            dynamic_spread = True

        # 根据 HIST 趋势强度调整 spread
        hist_factor = _get_hist_spread_factor(hist_mean_abs)
        spread = spread_base * hist_factor
        grid_adjusted = (hist_factor != 1.0)  # 标记是否进行了调整

        # ATR 相关数值（用于显示）
        atr_value = atr
        atr_pct_value = (atr / base_price * 100) if base_price != 0 else None

        # 计算 MACD 偏离度（价格相对 MACD 值的百分比偏离）
        ma_deviation = (close - macd_val) / abs(macd_val) * 100 if macd_val != 0 else 0

        # 计算持仓比例（价格越低持仓越高）
        half = spread / 2
        lower_price = base_price * (1 - half)
        upper_price = base_price * (1 + half)
        range_width = upper_price - lower_price
        if range_width > 0:
            dist_from_bottom = (close - lower_price) / range_width
            position_ratio = 1.0 - dist_from_bottom
        else:
            position_ratio = 0.5
        position_ratio = max(0.0, min(1.0, round(position_ratio, 4)))

        # 计算网格各档位价格
        grid_prices = np.linspace(lower_price, upper_price, grid_count + 1)
        current_index = int(np.searchsorted(grid_prices, close))
        current_index = min(max(current_index, 0), grid_count)

        # 根据价格位置生成交易信号
        if current_index <= 1:
            # 价格在网格底部区域，MACD 处于低位
            action = "买入"
            action_desc = f"MACD{macd_ma_key.replace('MACD_','')}低位，趋势弱，可买入"
        elif current_index >= grid_count - 2:
            # 价格在网格顶部区域，MACD 处于高位
            action = "卖出"
            action_desc = f"MACD{macd_ma_key.replace('MACD_','')}高位，趋势强，逢高减仓"
        elif position_ratio >= 0.75:
            # 持仓比例较高，趋势偏多
            action = "持有"
            action_desc = f"HIST均值偏正，趋势偏多，继续持有"
        elif position_ratio <= 0.25:
            # 持仓比例较低，趋势偏空
            action = "观望"
            action_desc = f"HIST均值偏负，趋势偏空，轻仓等待"
        else:
            # 中性区域
            action = "持有"
            action_desc = f"价格在{ macd_ma_key.replace('MACD_','') }中位，网格中位持仓"

        ma_key_for_label = macd_ma_key  # 兼容 base_label
        step_size = grid_prices[1] - grid_prices[0]

    else:
        # ==================== 均线锚定模式 ====================
        ma_val = float(latest.get(ma_key, 0))

        # 基准价设置：优先用选定均线，无则用收盘价
        if ma_val > 0:
            base_price = ma_val
            base_label = f"{ma_key}={ma_val:.4f}"
        else:
            base_price = close
            base_label = f"收盘价={close:.4f}"

        # ATR 动态区间计算
        atr = float(latest.get('ATR', 0))
        if atr <= 0 or grid_spread is not None:
            # ATR 无效或手动指定了 spread
            spread = grid_spread if grid_spread is not None else DEFAULT_GRID_SPREAD
            dynamic_spread = False
            atr_value = None
            atr_pct_value = None
        else:
            # 动态计算：总幅度 = 4×ATR / 基准价，限制在 5%~30%
            atr_pct_raw = (4 * atr) / base_price
            spread = max(0.05, min(0.30, atr_pct_raw))
            dynamic_spread = True
            atr_value = atr
            atr_pct_value = atr_pct_raw * 100

        # 计算均线偏离度（价格相对均线的百分比偏离）
        ma_deviation = (close - ma_val) / ma_val * 100 if ma_val > 0 else 0

        # 网格上下边界以基准价（均线）为中心
        half = spread / 2
        lower_price = base_price * (1 - half)
        upper_price = base_price * (1 + half)

        # 使用等差数列生成各格价格（从低到高）
        grid_prices = np.linspace(lower_price, upper_price, grid_count + 1)
        step_size = grid_prices[1] - grid_prices[0]

        # 当前价格所在格序
        current_index = int(np.searchsorted(grid_prices, close))
        current_index = min(max(current_index, 0), grid_count)

        # 持仓比例计算
        # 公式：持仓比例 = 1 - (当前价 - 下界) / 区间总宽度
        # 价格越接近下界（网格底），持仓越高；接近上界，持仓越低
        range_width = upper_price - lower_price
        if range_width > 0:
            dist_from_bottom = (close - lower_price) / range_width
            position_ratio = 1.0 - dist_from_bottom
        else:
            position_ratio = 0.5

        position_ratio = max(0.0, min(1.0, position_ratio))
        position_ratio = round(position_ratio, 4)

        # 根据价格位置生成交易信号
        if current_index <= 1:
            # 价格接近网格底部区域
            action = "买入"
            action_desc = "价格接近网格底部区域，低位加仓时机"
        elif current_index >= grid_count - 2:
            # 价格进入网格上部区域
            action = "卖出"
            action_desc = "价格进入网格上部区域，逢高减仓止盈"
        elif position_ratio >= 0.75:
            # 持仓比例较高，价格在均线下方
            action = "持有"
            action_desc = f"价格接近{ma_key}下方，仓位充足，耐心持有"
        elif position_ratio <= 0.25:
            # 持仓比例较低，价格在均线上方较远
            action = "观望"
            action_desc = f"价格高于{ma_key}较多，轻仓等待"
        else:
            # 中性区域
            action = "持有"
            action_desc = f"价格在{ma_key}附近，网格中位持仓"

        # MACD 相关字段设为 None（均线模式不使用）
        hist_current = None
        hist_mean = None
        hist_mean_abs = None
        grid_adjusted = False
        ma_key_for_label = ma_key
        step_size = grid_prices[1] - grid_prices[0]

    # ========== 统一构建返回结果 ==========
    # 生成带 emoji 的信号文本
    action_emoji = {"买入": "📈", "卖出": "📉", "持有": "➡️", "观望": "⚠️"}.get(action, "➡️")
    signal_text = (
        f"{action_emoji} {action}：{action_desc}，"
        f"建议持仓{int(position_ratio * 100)}%"
    )

    result = {
        'signal_name': '网格交易',
        'signal': action,
        'signal_text': signal_text,
        'close': close,
        'ma_key': ma_key_for_label,
        'ma_val': base_price,
        'ma_deviation_pct': round(ma_deviation, 3),
        'base_price': round(base_price, 6),
        'base_label': base_label,
        'atr': atr_value,
        'atr_pct': atr_pct_value,
        'dynamic_spread': dynamic_spread,
        'grid_count': int(grid_count),
        'grid_spread_pct': round(spread * 100, 3),
        'step_pct': round(step_size / base_price * 100, 3),
        'lower_bound': round(lower_price, 6),
        'upper_bound': round(upper_price, 6),
        'current_grid': current_index,
        'total_grids': grid_count,
        'position_ratio': position_ratio,
        'nearby_lower': round(grid_prices[max(current_index - 1, 0)], 6),
        'nearby_upper': round(grid_prices[min(current_index + 1, grid_count)], 6),
        'action_desc': action_desc,
    }

    # MACD 锚定模式额外字段
    if use_macd_mode:
        result['macd_ma_key'] = macd_ma_key
        result['macd_hist_mean'] = round(float(hist_mean), 6) if hist_mean is not None else None
        result['macd_hist_current'] = round(float(hist_current), 6) if hist_current is not None else None
        result['grid_adjusted'] = grid_adjusted

    return result


def format_grid_text(signal: Dict[str, Any]) -> str:
    """
    将网格信号格式化为可读的文本报告。

    将 get_grid_signal 返回的字典格式化为多行文本，
    便于在终端、日志或消息中展示。

    Parameters
    ----------
    signal : Dict[str, Any]
        网格信号字典，由 get_grid_signal 函数返回

    Returns
    -------
    str
        格式化后的多行文本，包含：
        - 网格交易参数（基准价、区间、格数、步长等）
        - 当前状态（格位、操作建议、持仓比例）
        - 今日网格信号
    """
    # 根据信号类型选择对应的 emoji
    action_emoji = {"买入": "📈", "卖出": "📉", "持有": "➡️"}.get(signal['signal'], "➡️")

    lines = []
    # 网格参数部分
    lines.append(f"📊 网格交易参数")
    lines.append(f"  • 基准价: {signal['close']:.4f}")
    lines.append(f"  • 网格区间: ±{signal['grid_spread_pct']:.1f}%")
    lines.append(f"  • 网格格数: {signal['grid_count']}格")
    lines.append(f"  • 每格步长: {signal['step_pct']:.2f}%")
    lines.append(f"  • 网格范围: {signal['lower_bound']:.4f} ~ {signal['upper_bound']:.4f}")
    lines.append("")
    # 当前状态部分
    lines.append(f"📍 当前状态")
    lines.append(f"  • 所在格位: 第{signal['current_grid']}格（共{signal['total_grids']}格）")
    lines.append(f"  • {signal['action_desc']}")
    lines.append(f"  • 建议持仓: {int(signal['position_ratio']*100)}%")
    lines.append("")
    # 信号部分
    lines.append(f"{action_emoji} 今日网格信号: {signal['signal']}")

    return "\n".join(lines)


def get_ma_trend_signal(latest: pd.Series,
                        fast_ma_key: str = 'MA5',
                        slow_ma_key: str = 'MA20',
                        position_size: float = 1.0) -> Dict[str, Any]:
    """
    MA 趋势跟踪策略信号生成。

    基于快慢均线交叉和价格与均线的关系，判断趋势方向并生成交易信号。
    适用于趋势明显的市场，在震荡市中可能产生较多假信号。

    ====================
    核心逻辑
    ====================
    - 快线 > 慢线 且 价格 > 慢线 → 多头趋势，买入 / 加仓
    - 快线 < 慢线 且 价格 < 慢线 → 空头趋势，卖出 / 减仓
    - 其他情况 → 持有 / 观望

    持仓比例基于趋势强度动态调整：
    - 快慢线偏离度越大 → 趋势越强 → 持仓比例越高（多头）或越低（空头）

    Parameters
    ----------
    latest : pd.Series
        最新行情数据，需包含以下字段：
        - 收盘：收盘价
        - MA5/MA10/MA20/MA60：各周期均线值
    fast_ma_key : str, optional
        快线均线字段名，默认为 'MA5'
        快线对价格变化更敏感，用于捕捉短期趋势
    slow_ma_key : str, optional
        慢线均线字段名，默认为 'MA20'
        慢线更平滑，用于确认趋势方向
    position_size : float, optional
        单次交易最大仓位比例，默认为 1.0
        范围：0.1 ~ 1.0，用于控制单次交易风险

    Returns
    -------
    Dict[str, Any]
        信号结果字典，包含以下字段：
        - signal_name: 信号名称
        - signal: 操作信号（"买入"/"卖出"/"持有"/"观望"）
        - signal_text: 信号文本描述
        - close: 当前收盘价
        - ma_key: 使用的均线组合
        - ma_deviation_pct: 快慢线偏离百分比
        - position_ratio: 建议持仓比例
        - step_pct: 步长百分比（固定为 1.0）
        - action_desc: 操作描述
    """
    close = float(latest['收盘'])
    fast_ma = float(latest.get(fast_ma_key, 0))
    slow_ma = float(latest.get(slow_ma_key, 0))

    # 数据校验：均线数据不足时返回观望信号
    if fast_ma <= 0 or slow_ma <= 0:
        return {
            'signal_name': 'MA趋势跟踪',
            'signal': '观望',
            'signal_text': f'⚠️ 均线数据不足 ({fast_ma_key}={fast_ma:.4f}, {slow_ma_key}={slow_ma:.4f})',
            'close': close,
            'position_ratio': 0.5,
            'step_pct': 1.0,
            'action_desc': '数据不足，暂时观望',
        }

    # 计算均线偏离度
    ma_deviation = (fast_ma - slow_ma) / slow_ma * 100  # 快慢线偏离度
    price_vs_slow = (close - slow_ma) / slow_ma * 100   # 价格相对慢线偏离度

    # 多头趋势判断：快线 > 慢线 且 价格 > 慢线
    if fast_ma > slow_ma and close > slow_ma:
        # 计算趋势强度（偏离度越大，趋势越强）
        strength = min(abs(ma_deviation) / 5.0, 1.0)
        position_ratio = round(0.5 + strength * 0.5, 4)  # 基础 50% + 强度加成
        position_ratio = min(position_ratio, position_size)  # 不超过最大仓位

        # 超买判断：价格远离慢线过多，考虑减仓
        if price_vs_slow > 3.0:
            signal = "卖出"
            action_desc = f"价格远离{slow_ma_key} {price_vs_slow:.1f}%，超买减仓"
            position_ratio = round(max(0.1, position_ratio * 0.5), 4)  # 减半持仓
        else:
            signal = "买入"
            action_desc = f"{fast_ma_key} > {slow_ma_key}，多头排列，趋势向上 (偏离{ma_deviation:.1f}%)"

    # 空头趋势判断：快线 < 慢线 且 价格 < 慢线
    elif fast_ma < slow_ma and close < slow_ma:
        # 计算趋势强度
        strength = min(abs(ma_deviation) / 5.0, 1.0)
        position_ratio = round(0.5 - strength * 0.5, 4)  # 基础 50% - 强度减仓
        position_ratio = max(0.0, position_ratio)

        # 超卖判断：价格远离慢线过多，考虑反弹买入
        if price_vs_slow < -3.0:
            signal = "买入"
            action_desc = f"价格远离{slow_ma_key} {abs(price_vs_slow):.1f}%，超卖反弹买入"
            position_ratio = round(min(position_size, position_ratio + 0.2), 4)  # 适当加仓
        else:
            signal = "卖出"
            action_desc = f"{fast_ma_key} < {slow_ma_key}，空头排列，趋势向下 (偏离{abs(ma_deviation):.1f}%)"

    # 均线粘合/震荡区域
    else:
        signal = "持有"
        action_desc = f"价格在{fast_ma_key}/{slow_ma_key}附近，均线粘合，等待方向选择"
        position_ratio = 0.5

    # 生成带 emoji 的信号文本
    action_emoji = {"买入": "📈", "卖出": "📉", "持有": "➡️"}.get(signal, "➡️")
    signal_text = (
        f"{action_emoji} {signal}：{action_desc}，"
        f"建议持仓{int(position_ratio * 100)}%"
    )

    return {
        'signal_name': 'MA趋势跟踪',
        'signal': signal,
        'signal_text': signal_text,
        'close': close,
        'ma_key': f'{fast_ma_key}/{slow_ma_key}',
        'ma_deviation_pct': round(ma_deviation, 3),
        'position_ratio': position_ratio,
        'step_pct': 1.0,
        'action_desc': action_desc,
    }
