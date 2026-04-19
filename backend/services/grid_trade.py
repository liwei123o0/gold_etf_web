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


# 默认网格参数
DEFAULT_GRID_COUNT = 10       # 网格格数
DEFAULT_GRID_SPREAD = 0.10    # 网格区间总幅度（上下10%，即 ±5%）
DEFAULT_BASE_RATIO = 0.50     # 基准价在网格区间的位置（0.5=中间）

# 有效的 MACD 基准类型
VALID_MACD_MA_KEYS = ('MACD', 'MACD_SIGNAL')

# MACD 基准模式下，HIST 均值对网格系数的映射
# key: MACD_HIST N日均值绝对值的分档阈值（单位：与价格同一量纲）
# value: spread 乘数（>1 扩大，<1 缩小）
_MACD_HIST_SPREAD_FACTOR = {
    (0.000, 0.002): 0.80,   # 震荡市场，缩小网格（降低成本）
    (0.002, 0.005): 1.00,  # 正常市场
    (0.005, 0.010): 1.20,  # 趋势偏强，适当扩大
    (0.010, float('inf')): 1.50,  # 强趋势，扩大网格（避免频繁触发）
}


def calc_grid_params(close: float,
                     grid_count: int = DEFAULT_GRID_COUNT,
                     grid_spread: float = DEFAULT_GRID_SPREAD,
                     base_ratio: float = DEFAULT_BASE_RATIO) -> Dict[str, Any]:
    """
    计算网格交易参数。

    Parameters
    ----------
    close : float
        当前收盘价（作为基准价）
    grid_count : int
        网格格数（默认10格）
    grid_spread : float
        网格总幅度（默认0.10 = 上下10%，即±5%）
    base_ratio : float
        基准价在网格的位置（0.0=最底部，1.0=最顶部，默认0.5=中间）

    Returns
    -------
    Dict
        包含网格各档位价格、当前所在格、止盈止损等
    """
    # 计算网格上下边界
    half = grid_spread / 2
    lower_price = close * (1 - half)
    upper_price = close * (1 + half)

    # 各格价格（从低到高）
    grid_prices = np.linspace(lower_price, upper_price, grid_count + 1)
    step_size = grid_prices[1] - grid_prices[0]

    # 基准价在网格中的位置
    base_price = close
    base_index = np.searchsorted(grid_prices, base_price)
    base_index = min(max(base_index, 0), grid_count)

    # 当前价格在网格中的格序（0=最低格，grid_count=最高格）
    current_index = np.searchsorted(grid_prices, close)
    current_index = min(max(current_index, 0), grid_count)

    # 计算每格收益率
    grid_returns = []
    for i in range(len(grid_prices) - 1):
        ret = (grid_prices[i + 1] - grid_prices[i]) / grid_prices[i] * 100
        grid_returns.append(ret)

    # 距离上下边界的格数
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

    Parameters
    ----------
    close : float
        当前价格
    grid_prices : List[float]
        网格各档位价格（低到高）

    Returns
    -------
    Dict
        当前格位、建议操作、持仓比例
    """
    n = len(grid_prices) - 1  # 格数（价格档位数-1）
    idx = np.searchsorted(grid_prices, close)
    idx = min(max(idx, 0), n)

    # 各格建议：
    # - 价格 <= 当前格下限：买入（一格）
    # - 价格在中间：持有
    # - 价格 >= 当前格上限：卖出（一格）
    lower = grid_prices[max(idx - 1, 0)]
    upper = grid_prices[min(idx + 1, n)]

    # 当前格距离（0=最低格，n=最高格）
    position_pct = idx / n * 100

    # 判断操作
    if idx == 0:
        action = "买入"
        action_desc = "价格触及网格底部，建议买入建仓"
    elif idx == n:
        action = "卖出"
        action_desc = "价格触及网格顶部，建议止盈卖出"
    elif close <= lower:
        action = "买入"
        action_desc = f"价格跌破格{int(idx-1)}线，建议买入"
    elif close >= upper:
        action = "卖出"
        action_desc = f"价格升破格{int(idx+1)}线，建议卖出"
    else:
        action = "持有"
        action_desc = "价格在网格中位，持有观望"

    # 建议持仓比例（线性：底部100%，顶部0%）
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
    根据 MACD_HIST 历史均值绝对值返回网格区间系数。

    Parameters
    ----------
    hist_mean_abs : float
        MACD_HIST 的 N 日均值（取绝对值）

    Returns
    -------
    float
        spread 乘数（0.8 ~ 1.5）
    """
    for (low, high), factor in _MACD_HIST_SPREAD_FACTOR.items():
        if low <= hist_mean_abs < high:
            return factor
    return 1.0


def get_grid_signal(latest: pd.Series,
                    grid_count: int = DEFAULT_GRID_COUNT,
                    grid_spread: float = None,
                    ma_key: str = 'MA20',
                    macd_ma_key: str = None,
                    macd_hist_window: int = 20,
                    macd_hist_mean: float = None) -> Dict[str, Any]:
    """
    生成网格交易信号（均线锚定 或 MACD锚定 动态网格）。

    模式一：均线锚定（ma_key 指定均线，默认 MA20）
    ----------------------------------------------------
    - 基准价 = 选定均线值（非当日收盘价）
      → 锚定市场平均成本，避免基准价随每日收盘价飘移
    - 区间 = 均线 ± 2×ATR（约覆盖 ±2ATR 的价格波动范围）
    - 持仓比例 = 1 - (当前价 - 下界) / 区间总宽度
      → 价格跌破均线越多，持仓越高（逢低加仓）
      → 价格涨超均线越多，持仓越低（逢高减仓）

    模式二：MACD锚定（macd_ma_key 指定 MACD 指标类型）
    ----------------------------------------------------
    - 基准价 = 当前 MACD/DIF 值或 MACD_SIGNAL/DEA 值
      → 以 MACD 指标值本身作为网格基准（价格量纲相同）
    - 区间宽度根据 MACD_HIST 的历史均值动态调整：
      * HIST 均值大（趋势强）→ spread × 系数扩大网格（避免频繁触发）
      * HIST 均值小（震荡） → spread × 系数缩小网格（降低成本）
    - 持仓比例同模式一

    Parameters
    ----------
    latest : pd.Series
        最新行情数据（含收盘价、各均线值、ATR，以及 MACD/SIGNAL/HIST）
    grid_count : int
        网格格数（默认10格）
    grid_spread : float, optional
        手动指定网格总幅度。不指定时：
        - MA模式：自动根据ATR计算（限制在 5%~30%）
        - MACD模式：使用 DEFAULT_GRID_SPREAD × HIST系数
    ma_key : str
        基准均线字段名（默认'MA20'，可选'MA5'/'MA10'/'MA20'/'MA60'）
        仅在 macd_ma_key 未指定时生效。
    macd_ma_key : str, optional
        MACD基准类型（可选 'MACD' 或 'MACD_SIGNAL'）。
        传入此参数后切换到 MACD 锚定模式，忽略 ma_key。
    macd_hist_window : int
        计算 MACD_HIST 历史均值的窗口天数（默认20天）。
    macd_hist_mean : float, optional
        MACD_HIST 的历史均值（由调用方从完整数据列计算后传入）。
        MACD 锚定模式下必须传入，否则 spread 系数默认1.0。

    Returns
    -------
    Dict
        网格信号，包含参数和持仓建议。
        新增字段（MACD 锚定模式）：
        - macd_ma_key: 使用的MACD均值类型
        - macd_hist_mean: MACD_HIST 的历史均值（用于判断趋势强度）
        - macd_hist_current: 当前 MACD_HIST 值
        - grid_adjusted: 是否因MACD趋势调整了网格参数
    """
    close = float(latest['收盘'])

    # ========== 判断使用哪种基准模式 ==========
    use_macd_mode = macd_ma_key in VALID_MACD_MA_KEYS

    if use_macd_mode:
        # -------- MACD 锚定模式 --------
        macd_val = float(latest.get(macd_ma_key, 0))
        hist_current = float(latest.get('MACD_HIST', 0))

        # MACD_HIST 历史均值由调用方计算后传入
        if macd_hist_mean is not None:
            hist_mean_abs = abs(macd_hist_mean)
        else:
            hist_mean_abs = 0.0

        # 基准价
        if macd_val > 0:
            base_price = macd_val
            base_label = f"{macd_ma_key}={macd_val:.6f}"
        else:
            base_price = close
            base_label = f"收盘价={close:.4f}（{macd_ma_key}无数据）"

        # ATR 动态区间（MACD模式也用ATR做基础spread）
        atr = float(latest.get('ATR', 0))
        if atr <= 0 or grid_spread is not None:
            spread_base = grid_spread if grid_spread is not None else DEFAULT_GRID_SPREAD
            dynamic_spread = False
        else:
            spread_base = (4 * atr) / base_price if base_price != 0 else DEFAULT_GRID_SPREAD
            spread_base = max(0.05, min(0.30, spread_base))
            dynamic_spread = True

        # 根据 HIST 趋势强度调整 spread
        hist_factor = _get_hist_spread_factor(hist_mean_abs)
        spread = spread_base * hist_factor
        grid_adjusted = (hist_factor != 1.0)

        # 均线基准模式下不需要 ATR 显示（但 MACD 模式需要告知）
        atr_value = atr
        atr_pct_value = (atr / base_price * 100) if base_price != 0 else None

        # 均线偏离度改为 MACD 偏离度（相对基准价的百分比）
        ma_deviation = (close - macd_val) / abs(macd_val) * 100 if macd_val != 0 else 0

        # 持仓比例计算（与 MA 模式相同逻辑）
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

        # 信号判断（基于价格相对网格的位置）
        grid_prices = np.linspace(lower_price, upper_price, grid_count + 1)
        current_index = int(np.searchsorted(grid_prices, close))
        current_index = min(max(current_index, 0), grid_count)

        if current_index <= 1:
            action = "买入"
            action_desc = f"MACD{macd_ma_key.replace('MACD_','')}低位，趋势弱，可买入"
        elif current_index >= grid_count - 1:
            action = "卖出"
            action_desc = f"MACD{macd_ma_key.replace('MACd_','')}高位，趋势强，逢高减仓"
        elif position_ratio >= 0.75:
            action = "持有"
            action_desc = f"HIST均值偏正，趋势偏多，继续持有"
        elif position_ratio <= 0.25:
            action = "观望"
            action_desc = f"HIST均值偏负，趋势偏空，轻仓等待"
        else:
            action = "持有"
            action_desc = f"价格在{ macd_ma_key.replace('MACD_','') }中位，网格中位持仓"

        ma_key_for_label = macd_ma_key  # 兼容 base_label

    else:
        # -------- 均线锚定模式（原有逻辑）--------
        ma_val = float(latest.get(ma_key, 0))

        # 基准价：优先用选定均线，无则用收盘价
        if ma_val > 0:
            base_price = ma_val
            base_label = f"{ma_key}={ma_val:.4f}"
        else:
            base_price = close
            base_label = f"收盘价={close:.4f}"

        # ATR 动态区间
        atr = float(latest.get('ATR', 0))
        if atr <= 0 or grid_spread is not None:
            spread = grid_spread if grid_spread is not None else DEFAULT_GRID_SPREAD
            dynamic_spread = False
            atr_value = None
            atr_pct_value = None
        else:
            # 动态：总幅度 = 4×ATR / 基准价，限制在 5%~30%
            atr_pct_raw = (4 * atr) / base_price
            spread = max(0.05, min(0.30, atr_pct_raw))
            dynamic_spread = True
            atr_value = atr
            atr_pct_value = atr_pct_raw * 100

        # 均线偏离度
        ma_deviation = (close - ma_val) / ma_val * 100 if ma_val > 0 else 0

        # 网格上下边界以基准价（均线）为中心
        half = spread / 2
        lower_price = base_price * (1 - half)
        upper_price = base_price * (1 + half)

        # 各格价格（从低到高）
        grid_prices = np.linspace(lower_price, upper_price, grid_count + 1)
        step_size = grid_prices[1] - grid_prices[0]

        # 当前价格所在格序
        current_index = int(np.searchsorted(grid_prices, close))
        current_index = min(max(current_index, 0), grid_count)

        # 持仓比例 = 1 - (当前价 - 下界) / 区间总宽度
        # 价格越接近下界（网格底），持仓越高；接近上界，持仓越低
        range_width = upper_price - lower_price
        if range_width > 0:
            dist_from_bottom = (close - lower_price) / range_width
            position_ratio = 1.0 - dist_from_bottom
        else:
            position_ratio = 0.5

        position_ratio = max(0.0, min(1.0, position_ratio))
        position_ratio = round(position_ratio, 4)

        # 判断操作信号
        if current_index <= 1:
            action = "买入"
            action_desc = "价格接近网格底部区域，低位加仓时机"
        elif current_index >= grid_count - 1:
            action = "卖出"
            action_desc = "价格触及网格顶部区域，逢高减仓止盈"
        elif position_ratio >= 0.75:
            action = "持有"
            action_desc = f"价格低于{ma_key}，仓位充足，耐心持有"
        elif position_ratio <= 0.25:
            action = "观望"
            action_desc = f"价格高于{ma_key}较多，轻仓或空仓，等待回落"
        else:
            action = "持有"
            action_desc = f"价格在{ma_key}附近，网格中位持仓"

        # MACD 相关字段设为 None
        hist_current = None
        hist_mean = None
        hist_mean_abs = None
        grid_adjusted = False
        ma_key_for_label = ma_key
        step_size = grid_prices[1] - grid_prices[0]

    # ========== 统一构建返回结果 ==========
    # （各分支已正确计算 lower_price, upper_price, grid_prices, current_index, step_size, spread）
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
    将网格信号格式化为文本。

    Returns
    -------
    str
        格式化文本
    """
    action_emoji = {"买入": "📈", "卖出": "📉", "持有": "➡️"}.get(signal['signal'], "➡️")

    lines = []
    lines.append(f"📊 网格交易参数")
    lines.append(f"  • 基准价: {signal['close']:.4f}")
    lines.append(f"  • 网格区间: ±{signal['grid_spread_pct']:.1f}%")
    lines.append(f"  • 网格格数: {signal['grid_count']}格")
    lines.append(f"  • 每格步长: {signal['step_pct']:.2f}%")
    lines.append(f"  • 网格范围: {signal['lower_bound']:.4f} ~ {signal['upper_bound']:.4f}")
    lines.append("")
    lines.append(f"📍 当前状态")
    lines.append(f"  • 所在格位: 第{signal['current_grid']}格（共{signal['total_grids']}格）")
    lines.append(f"  • {signal['action_desc']}")
    lines.append(f"  • 建议持仓: {int(signal['position_ratio']*100)}%")
    lines.append("")
    lines.append(f"{action_emoji} 今日网格信号: {signal['signal']}")

    return "\n".join(lines)
