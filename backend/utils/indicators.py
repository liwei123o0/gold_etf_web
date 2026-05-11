"""
技术指标计算模块

提供各种技术指标的计算函数，支持 Pandas DataFrame 的链式调用。
所有函数接收一个 DataFrame（必须包含 '开盘','最高','最低','收盘','成交量' 列），
返回添加了对应指标列的 DataFrame（不修改原对象）。

支持的指标：
    - 移动平均线（MA5/MA10/MA20/MA60）
    - 涨跌幅和涨跌额
    - MACD（指数平滑异同移动平均线）
    - KDJ（随机指标）
    - RSI（相对强弱指数）
    - 布林带（Bollinger Bands）
    - 资金流向
    - OBV（能量潮）
    - 年化波动率
    - ATR（真实波幅均值）
"""

import numpy as np
import pandas as pd


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    计算全部技术指标（主入口函数）

    包含：均线、涨跌幅、MACD、KDJ、RSI、布林带、资金流向、OBV、波动率、ATR。

    参数：
        df (pd.DataFrame): 输入数据，必须包含以下列：
            '开盘' - 开盘价
            '最高' - 最高价
            '最低' - 最低价
            '收盘' - 收盘价
            '成交量' - 成交量

    返回：
        pd.DataFrame: 在原 DataFrame 基础上新增以下列：
            MA5, MA10, MA20, MA60 - 移动平均线
            涨跌幅, 涨跌额 - 涨跌数据
            MACD, MACD_SIGNAL, MACD_HIST - MACD 指标
            K, D, J - KDJ 随机指标
            RSI - 相对强弱指数
            BB_MID, BB_UPPER, BB_LOWER - 布林带
            资金净流入, 累计净流入, 主力净流入, 主力占比 - 资金流向
            OBV - 能量潮指标
            VOLATILITY - 年化波动率
            ATR - 真实波幅均值
    """
    # 使用 copy 避免修改原始 DataFrame
    result = df.copy()

    # 依次计算各项技术指标
    _add_ma(result)          # 移动平均线
    _add_change(result)      # 涨跌幅和涨跌额
    _add_macd(result)        # MACD 指标
    _add_kdj(result)         # KDJ 随机指标
    _add_rsi(result)         # RSI 相对强弱指数
    _add_bollinger(result)   # 布林带
    _add_money_flow(result)  # 资金流向
    _add_obv(result)         # OBV 能量潮
    _add_volatility(result)  # 年化波动率
    _add_atr(result)         # ATR 真实波幅均值（动态网格用）

    return result


# ------------------------------------------------------------------
# 内部辅助函数（非公开 API）
# ------------------------------------------------------------------

def _add_ma(df: pd.DataFrame) -> None:
    """
    添加移动平均线指标

    计算 MA5（5日）、MA10（10日）、MA20（20日）、MA60（60日）移动平均线。
    """
    df['MA5'] = df['收盘'].rolling(5).mean()    # 5日均线
    df['MA10'] = df['收盘'].rolling(10).mean()   # 10日均线
    df['MA20'] = df['收盘'].rolling(20).mean()   # 20日均线
    df['MA60'] = df['收盘'].rolling(60).mean()   # 60日均线


def _add_change(df: pd.DataFrame) -> None:
    """
    添加涨跌幅和涨跌额指标

    涨跌幅 = 当日收盘价相对前日收盘价的百分比变化
    涨跌额 = 当日收盘价减去前日收盘价
    """
    df['涨跌幅'] = df['收盘'].pct_change() * 100  # 涨跌幅（%）
    df['涨跌额'] = df['收盘'].diff()               # 涨跌额（元）


def _add_macd(df: pd.DataFrame) -> None:
    """
    添加 MACD 系列指标

    MACD（指数平滑异同移动平均线）计算方式：
        MACD（DIF）= EMA12 - EMA26
        MACD_SIGNAL（DEA）= MACD 的 9 日 EMA
        MACD_HIST（柱状图）= MACD - MACD_SIGNAL
    """
    ema12 = df['收盘'].ewm(span=12, adjust=False).mean()  # 12日指数移动平均
    ema26 = df['收盘'].ewm(span=26, adjust=False).mean()  # 26日指数移动平均
    df['MACD'] = ema12 - ema26                              # MACD 线（DIF）
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()  # 信号线（DEA）
    df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']        # MACD 柱状图


def _add_kdj(df: pd.DataFrame) -> None:
    """
    添加 KDJ 随机指标

    KDJ 计算方式：
        RSV = (收盘价 - 9日最低价) / (9日最高价 - 9日最低价) × 100
        K = RSV 的 3日指数移动平均
        D = K 的 3日指数移动平均
        J = 3K - 2D
    """
    low9 = df['最低'].rolling(9).min()   # 9日最低价
    high9 = df['最高'].rolling(9).max()  # 9日最高价
    rsv = (df['收盘'] - low9) / (high9 - low9) * 100  # 未成熟随机值
    df['K'] = rsv.ewm(com=2, adjust=False).mean()      # K 值
    df['D'] = df['K'].ewm(com=2, adjust=False).mean()   # D 值
    df['J'] = 3 * df['K'] - 2 * df['D']                 # J 值


def _add_rsi(df: pd.DataFrame) -> None:
    """
    添加 RSI 相对强弱指数（14日）

    RSI 计算方式：
        RSI = 100 - 100 / (1 + RS)
        RS = 14日平均涨幅 / 14日平均跌幅
    """
    delta = df['收盘'].diff()  # 日涨跌
    gain = delta.where(delta > 0, 0).rolling(14).mean()   # 14日平均涨幅
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()  # 14日平均跌幅
    rs = gain / loss  # 相对强弱比
    df['RSI'] = 100 - (100 / (1 + rs))  # RSI 值


def _add_bollinger(df: pd.DataFrame) -> None:
    """
    添加布林带指标（20日，2倍标准差）

    布林带计算方式：
        BB_MID = 20日移动平均线（中轨）
        BB_UPPER = BB_MID + 2 × 20日标准差（上轨）
        BB_LOWER = BB_MID - 2 × 20日标准差（下轨）
    """
    df['BB_MID'] = df['收盘'].rolling(20).mean()  # 中轨（20日均线）
    bb_std = df['收盘'].rolling(20).std()          # 20日标准差
    df['BB_UPPER'] = df['BB_MID'] + 2 * bb_std    # 上轨
    df['BB_LOWER'] = df['BB_MID'] - 2 * bb_std    # 下轨


def _add_money_flow(df: pd.DataFrame) -> None:
    """
    添加资金流向指标

    资金净流入 = 成交量 × 涨跌幅 / 100（简化估算）
    累计净流入 = 资金净流入的累计值
    主力净流入 = 资金净流入 × 0.7（假设主力占比70%）
    主力占比 = 主力净流入 / 成交量 × 100
    """
    df['资金净流入'] = df['成交量'] * df['涨跌幅'] / 100  # 资金净流入（简化估算）
    df['累计净流入'] = df['资金净流入'].cumsum()          # 累计净流入
    df['主力净流入'] = df['资金净流入'] * 0.7             # 主力净流入（假设70%为主力）
    df['主力占比'] = df['主力净流入'] / df['成交量'] * 100  # 主力占比（%）


def _add_obv(df: pd.DataFrame) -> None:
    """
    添加 OBV 能量潮指标

    OBV 计算方式：
        若今日收盘 > 昨日收盘：OBV += 今日成交量
        若今日收盘 < 昨日收盘：OBV -= 今日成交量
        若今日收盘 = 昨日收盘：OBV 不变
    """
    df['OBV'] = (np.sign(df['收盘'].diff()) * df['成交量']).cumsum()


def _add_volatility(df: pd.DataFrame) -> None:
    """
    添加年化波动率指标（20日窗口）

    年化波动率 = 20日涨跌幅标准差 × √252 × 100
    其中 252 为一年的交易日数。
    """
    df['VOLATILITY'] = df['涨跌幅'].rolling(20).std() * np.sqrt(252) * 100


def _add_atr(df: pd.DataFrame, window: int = 20) -> None:
    """
    添加 ATR（Average True Range，真实波幅均值）指标

    ATR 用于衡量市场波动程度，常用于动态网格参数计算。

    真实波幅（TR）取以下三者的最大值：
        1. 当日最高价 - 当日最低价
        2. |当日最高价 - 昨日收盘价|
        3. |当日最低价 - 昨日收盘价|

    ATR = TR 的 N 日移动平均（默认 20 日）

    参数：
        df (pd.DataFrame): 输入数据
        window (int): ATR 计算窗口期，默认 20 日
    """
    high = df['最高']
    low = df['最低']
    prev_close = df['收盘'].shift(1)  # 昨日收盘价

    # 计算真实波幅的三个分量
    tr1 = high - low                          # 当日振幅
    tr2 = (high - prev_close).abs()           # 当日最高与昨收的差距
    tr3 = (low - prev_close).abs()            # 当日最低与昨收的差距

    # 取三者最大值作为真实波幅
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # 计算真实波幅的移动平均
    df['ATR'] = tr.rolling(window).mean()
