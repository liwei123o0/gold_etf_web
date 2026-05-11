"""
实时交易信号计算模块

接收实时价格数据，结合缓存的日线技术指标，重新计算交易信号。
用于盘中实时信号推送场景。
"""

from datetime import datetime
from typing import Optional

from backend.services.gold_data import get_full_data, generate_signals, get_grid_signal
from backend.utils.symbol import normalize_symbol


def _calc_trade_signal_from_latest(latest) -> str:
    """
    根据技术指标打分计算综合交易信号

    评分规则：
        - 收盘价 > MA5 且 MA5 > MA10（多头排列）：+1
        - 收盘价 < MA5 且 MA5 < MA10（空头排列）：-1
        - MACD 柱状图 > 0（多头动能）：+1
        - MACD 柱状图 < 0（空头动能）：-1
        - RSI > 70（超买）：-1
        - RSI < 30（超卖）：+1
        - J 值 > 80（超买）：-1
        - J 值 < 20（超卖）：+1

    参数：
        latest: 包含技术指标的 Series 或 dict，需包含 '收盘', 'MA5', 'MA10', 'MACD_HIST', 'RSI', 'J'

    返回：
        str: 交易信号，"买入"（得分≥2）、"卖出"（得分≤-2）或 "观望"
    """
    score = 0
    close = latest.get('收盘', 0)  # 当前收盘价
    ma5 = latest.get('MA5', 0)  # 5日均线
    ma10 = latest.get('MA10', 0)  # 10日均线
    macd_hist = latest.get('MACD_HIST', 0)  # MACD 柱状图
    rsi = latest.get('RSI', 0)  # RSI 相对强弱指数
    j = latest.get('J', 0)  # KDJ 的 J 值

    # 均线排列判断：多头排列加分，空头排列减分
    if close > ma5 and ma5 > ma10:
        score += 1
    elif close < ma5 and ma5 < ma10:
        score -= 1

    # MACD 柱状图方向判断
    if macd_hist > 0:
        score += 1
    elif macd_hist < 0:
        score -= 1

    # RSI 超买超卖判断
    if rsi > 70:
        score -= 1
    elif rsi < 30:
        score += 1

    # KDJ 的 J 值超买超卖判断
    if j > 80:
        score -= 1
    elif j < 20:
        score += 1

    # 根据综合得分返回信号
    if score >= 2:
        return "买入"
    elif score <= -2:
        return "卖出"
    else:
        return "观望"


def _calc_change_pct(realtime_price: float, prev_close: float) -> float:
    """
    计算实时涨跌幅（百分比）

    参数：
        realtime_price (float): 实时价格
        prev_close (float): 昨日收盘价

    返回：
        float: 涨跌幅百分比，昨收为 0 时返回 0.0
    """
    if not prev_close:
        return 0.0
    return (realtime_price - prev_close) / prev_close * 100


def safe(val, default=0.0):
    """
    安全取值函数，处理 pandas 中的 NaN 值

    参数：
        val: 待检查的值，可能是 NaN
        default: NaN 时的默认返回值，默认为 0.0

    返回：
        float: 如果 val 是 NaN 则返回 default，否则返回 float(val)
    """
    import pandas as pd
    if pd.isna(val):
        return default
    return float(val)


def calc_signaltime(
    symbol: str,
    realtime_price: float,
    prev_close: Optional[float] = None
) -> dict:
    """
    计算实时交易信号（主入口函数）

    根据实时价格替换最新日线数据中的收盘价，重新计算技术指标和交易信号。

    参数：
        symbol (str): 股票代码，如 "518880"、"sh518880"
        realtime_price (float): 实时价格
        prev_close (float, 可选): 昨日收盘价，不传则从历史数据中获取

    返回：
        dict: 信号结果字典，包含以下字段：
            - code (int): 状态码，0 表示成功
            - msg (str): 状态信息
            - symbol (str): 规范化后的股票代码
            - realtime_price (float): 实时价格
            - prev_close (float): 昨日收盘价
            - change_pct (float): 涨跌幅（%）
            - trade_signal (str): 综合交易信号（"买入"/"卖出"/"观望"）
            - signals (dict): 各项技术指标信号
            - grid_signals (dict): 各均线/MACD 的网格信号
            - grid_signal (dict): 基于 MA20 的默认网格信号
            - latest (dict): 最新技术指标数据
    """
    # 规范化股票代码
    symbol = normalize_symbol(symbol)

    # 获取最近 90 个交易日的日线数据（含技术指标）
    df = get_full_data(symbol=symbol, datalen=90)

    # 数据不足时返回错误
    if len(df) < 2:
        return {"error": "数据不足"}

    # 取最新一行数据作为基础
    latest = df.iloc[-1].copy()

    # 将实时价格转换为浮点数
    realtime_close = float(realtime_price)

    # 确定昨日收盘价：优先使用传入值，否则从历史数据中获取
    if prev_close:
        prev_close = float(prev_close)
    else:
        # 取倒数第二行的收盘价作为昨收
        prev_close = float(df.iloc[-2]['收盘']) if len(df) >= 2 else float(latest['收盘'])

    # 计算实时涨跌幅
    change_pct = _calc_change_pct(realtime_close, prev_close)

    # 用实时价格替换最新数据中的收盘价和涨跌幅
    latest['收盘'] = realtime_close
    latest['涨跌幅'] = change_pct

    # 基于实时价格重新生成技术指标信号
    signals = generate_signals(latest, df)

    # 计算综合交易信号
    trade_signal = _calc_trade_signal_from_latest(latest)

    # 计算 MACD_HIST 的 20 日历史均值，用于网格信号判断
    macd_hist_window = 20
    macd_hist_mean = df['MACD_HIST'].iloc[-macd_hist_window:].mean() if len(df) >= macd_hist_window else df['MACD_HIST'].mean()

    # 生成各均线和 MACD 的网格信号
    grid_signals = {
        'MA5': get_grid_signal(latest, ma_key='MA5'),
        'MA10': get_grid_signal(latest, ma_key='MA10'),
        'MA20': get_grid_signal(latest, ma_key='MA20'),
        'MA60': get_grid_signal(latest, ma_key='MA60'),
        'MACD': get_grid_signal(latest, macd_ma_key='MACD', macd_hist_window=macd_hist_window,
                                macd_hist_mean=macd_hist_mean),
        'MACD_SIGNAL': get_grid_signal(latest, macd_ma_key='MACD_SIGNAL', macd_hist_window=macd_hist_window,
                                       macd_hist_mean=macd_hist_mean),
    }
    # 默认使用 MA20 作为网格信号基准
    grid_signal = get_grid_signal(latest, ma_key='MA20')

    return {
        'code': 0,
        'msg': 'success',
        'symbol': symbol,
        'realtime_price': realtime_close,
        'prev_close': prev_close,
        'change_pct': round(change_pct, 2),
        'trade_signal': trade_signal,
        'signals': signals,
        'grid_signals': grid_signals,
        'grid_signal': grid_signal,
        'latest': {
            '收盘': realtime_close,
            '涨跌幅': round(change_pct, 2),
            'MA5': safe(latest['MA5']),
            'MA10': safe(latest['MA10']),
            'MA20': safe(latest['MA20']),
            'MA60': safe(latest['MA60']),
            'RSI': safe(latest['RSI']),
            'J': safe(latest['J']),
            'MACD': safe(latest['MACD']),
            'MACD_SIGNAL': safe(latest['MACD_SIGNAL']),
            'MACD_HIST': safe(latest['MACD_HIST']),
            'BB_UPPER': safe(latest.get('BB_UPPER', 0)),
            'BB_MID': safe(latest.get('BB_MID', 0)),
            'BB_LOWER': safe(latest.get('BB_LOWER', 0)),
            'ATR': safe(latest.get('ATR', 0)),
        }
    }
