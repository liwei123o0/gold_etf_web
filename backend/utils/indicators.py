"""
技术指标计算模块

提供各种技术指标的计算函数，支持 Pandas DataFrame 的链式调用。
所有函数接收一个 DataFrame（必须包含 '开盘','最高','最低','收盘','成交量' 列），
返回添加了对应指标列的 DataFrame（不修改原对象）。
"""

import numpy as np
import pandas as pd


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算全部技术指标（主入口函数）。

    包含：均线、涨跌幅、MACD、KDJ、RSI、布林带、资金流向、OBV、波动率。

    Parameters
    ----------
    df : pd.DataFrame
        必须包含列：'开盘','最高','最低','收盘','成交量'

    Returns
    -------
    pd.DataFrame
        新增以下列：
        MA5, MA10, MA20, 涨跌幅, 涨跌额,
        MACD, MACD_SIGNAL, MACD_HIST,
        K, D, J,
        RSI,
        BB_MID, BB_UPPER, BB_LOWER,
        资金净流入, 累计净流入, 主力净流入, 主力占比,
        OBV, VOLATILITY
    """
    # 使用 copy 避免修改原始 DataFrame
    result = df.copy()

    _add_ma(result)
    _add_change(result)
    _add_macd(result)
    _add_kdj(result)
    _add_rsi(result)
    _add_bollinger(result)
    _add_money_flow(result)
    _add_obv(result)
    _add_volatility(result)
    _add_atr(result)  # ATR（动态网格用）

    return result


# ------------------------------------------------------------------
# 内部辅助函数（非公开 API）
# ------------------------------------------------------------------

def _add_ma(df: pd.DataFrame) -> None:
    """添加移动平均线：MA5 / MA10 / MA20 / MA60"""
    df['MA5'] = df['收盘'].rolling(5).mean()
    df['MA10'] = df['收盘'].rolling(10).mean()
    df['MA20'] = df['收盘'].rolling(20).mean()
    df['MA60'] = df['收盘'].rolling(60).mean()


def _add_change(df: pd.DataFrame) -> None:
    """添加涨跌幅和涨跌额"""
    df['涨跌幅'] = df['收盘'].pct_change() * 100
    df['涨跌额'] = df['收盘'].diff()


def _add_macd(df: pd.DataFrame) -> None:
    """添加 MACD 系列指标"""
    ema12 = df['收盘'].ewm(span=12, adjust=False).mean()
    ema26 = df['收盘'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']


def _add_kdj(df: pd.DataFrame) -> None:
    """添加 KDJ 随机指标"""
    low9 = df['最低'].rolling(9).min()
    high9 = df['最高'].rolling(9).max()
    rsv = (df['收盘'] - low9) / (high9 - low9) * 100
    df['K'] = rsv.ewm(com=2, adjust=False).mean()
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']


def _add_rsi(df: pd.DataFrame) -> None:
    """添加 RSI 相对强弱指数（14日）"""
    delta = df['收盘'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))


def _add_bollinger(df: pd.DataFrame) -> None:
    """添加布林带（20日，2倍标准差）"""
    df['BB_MID'] = df['收盘'].rolling(20).mean()
    bb_std = df['收盘'].rolling(20).std()
    df['BB_UPPER'] = df['BB_MID'] + 2 * bb_std
    df['BB_LOWER'] = df['BB_MID'] - 2 * bb_std


def _add_money_flow(df: pd.DataFrame) -> None:
    """添加资金流向指标"""
    df['资金净流入'] = df['成交量'] * df['涨跌幅'] / 100
    df['累计净流入'] = df['资金净流入'].cumsum()
    df['主力净流入'] = df['资金净流入'] * 0.7
    df['主力占比'] = df['主力净流入'] / df['成交量'] * 100


def _add_obv(df: pd.DataFrame) -> None:
    """添加 OBV 能量潮指标"""
    df['OBV'] = (np.sign(df['收盘'].diff()) * df['成交量']).cumsum()


def _add_volatility(df: pd.DataFrame) -> None:
    """添加年化波动率（20日窗口）"""
    df['VOLATILITY'] = df['涨跌幅'].rolling(20).std() * np.sqrt(252) * 100


def _add_atr(df: pd.DataFrame, window: int = 20) -> None:
    """
    添加 ATR（Average True Range，真实波幅均值）。
    ATR = Max(High-Low, |High-PrevClose|, |Low-PrevClose|) 的移动平均
    用于动态网格参数计算。
    """
    high = df['最高']
    low = df['最低']
    prev_close = df['收盘'].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window).mean()
