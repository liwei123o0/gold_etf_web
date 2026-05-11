"""
多因子综合评分引擎

将多个技术指标按权重加权评分，输出综合分数和市场状态判断。
评分范围: -100 (极度看空) ~ +100 (极度看多)
市场状态: strong_bull / bull / neutral / bear / strong_bear

用于:
1. 自动交易调度器的信号增强
2. 自适应策略切换的市场环境判断
3. 前端展示综合评分
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional


# 各因子默认权重配置，所有权重之和为1.0
FACTOR_WEIGHTS = {
    "ma_trend": 0.20,      # 均线趋势因子权重
    "macd": 0.15,          # MACD因子权重
    "rsi": 0.15,           # RSI因子权重
    "kdj": 0.10,           # KDJ因子权重
    "bollinger": 0.10,     # 布林带因子权重
    "volume": 0.10,        # 成交量因子权重
    "fund_flow": 0.10,     # 资金流向因子权重
    "volatility": 0.10,    # 波动率因子权重
}


def _score_ma_trend(latest: pd.Series, df: pd.DataFrame) -> float:
    """
    计算均线趋势因子得分

    根据价格与多条均线（MA5/MA10/MA20/MA60）的位置关系和均线排列形态评分：
    - 收盘价 > MA5 > MA10：多头排列加分
    - 收盘价 < MA5 < MA10：空头排列减分
    - 收盘价与MA20的关系：上方加分，下方减分
    - MA5/MA10/MA20/MA60 多头/空头排列：大幅加减分
    - MA5与MA10的金叉/死叉：加减分

    Args:
        latest: 最新一行K线数据
        df: 完整K线历史数据

    Returns:
        float: 均线趋势因子得分，范围 -100 ~ +100
    """
    score = 0.0
    close = float(latest["收盘"])
    ma5 = float(latest.get("MA5", 0)) if not pd.isna(latest.get("MA5")) else 0
    ma10 = float(latest.get("MA10", 0)) if not pd.isna(latest.get("MA10")) else 0
    ma20 = float(latest.get("MA20", 0)) if not pd.isna(latest.get("MA20")) else 0
    ma60 = float(latest.get("MA60", 0)) if not pd.isna(latest.get("MA60")) else 0

    # 短期均线排列判断：收盘价与MA5、MA10的位置关系
    if ma5 > 0 and ma10 > 0:
        if close > ma5 > ma10:
            # 收盘价 > MA5 > MA10，强势多头
            score += 40
        elif close < ma5 < ma10:
            # 收盘价 < MA5 < MA10，强势空头
            score -= 40
        elif close > ma5:
            # 收盘价仅高于MA5，偏多
            score += 15
        elif close < ma5:
            # 收盘价仅低于MA5，偏空
            score -= 15

    # 中期均线判断：收盘价与MA20的关系
    if ma20 > 0:
        if close > ma20:
            score += 20
        else:
            score -= 20

    # 长期均线排列判断：四线多头/空头排列
    if ma20 > 0 and ma60 > 0:
        if ma5 > ma10 > ma20 > ma60:
            # 完美多头排列
            score += 40
        elif ma5 < ma10 < ma20 < ma60:
            # 完美空头排列
            score -= 40

    # 金叉死叉判断：MA5与MA10的交叉
    if len(df) >= 2:
        prev_ma5 = float(df["MA5"].iloc[-2]) if not pd.isna(df["MA5"].iloc[-2]) else None
        prev_ma10 = float(df["MA10"].iloc[-2]) if not pd.isna(df["MA10"].iloc[-2]) else None
        if prev_ma5 and prev_ma10:
            if ma5 > ma10 and prev_ma5 <= prev_ma10:
                # MA5上穿MA10，金叉
                score += 30
            elif ma5 < ma10 and prev_ma5 >= prev_ma10:
                # MA5下穿MA10，死叉
                score -= 30

    # 将得分限制在 -100 ~ +100 范围内
    return max(-100, min(100, score))


def _score_macd(latest: pd.Series, df: pd.DataFrame) -> float:
    """
    计算MACD因子得分

    根据MACD指标值（DIF、DEA、HIST）的正负和交叉关系评分：
    - DIF > 0：多头区域加分
    - DIF > DEA：DIF在DEA上方加分
    - HIST > 0：柱状图为正加分
    - DIF由负转正（零轴金叉）：大幅加分

    Args:
        latest: 最新一行K线数据
        df: 完整K线历史数据

    Returns:
        float: MACD因子得分，范围 -100 ~ +100
    """
    score = 0.0
    macd = float(latest.get("MACD", 0)) if not pd.isna(latest.get("MACD")) else 0
    macd_sig = float(latest.get("MACD_SIGNAL", 0)) if not pd.isna(latest.get("MACD_SIGNAL")) else 0
    macd_hist = float(latest.get("MACD_HIST", 0)) if not pd.isna(latest.get("MACD_HIST")) else 0

    # DIF线正负判断
    if macd > 0:
        score += 30
    else:
        score -= 30

    # DIF与DEA的大小关系
    if macd > macd_sig:
        score += 20
    else:
        score -= 20

    # 柱状图正负判断
    if macd_hist > 0:
        score += 20
    else:
        score -= 20

    # 零轴金叉/死叉判断：DIF由负转正或由正转负
    if len(df) >= 2:
        prev_macd = float(df["MACD"].iloc[-2]) if not pd.isna(df["MACD"].iloc[-2]) else None
        if prev_macd is not None:
            if macd > 0 and prev_macd <= 0:
                # DIF上穿零轴，强多头信号
                score += 30
            elif macd < 0 and prev_macd >= 0:
                # DIF下穿零轴，强空头信号
                score -= 30

    return max(-100, min(100, score))


def _score_rsi(latest: pd.Series) -> float:
    """
    计算RSI因子得分

    根据RSI值的区间映射评分：
    - RSI >= 80：极度超买，强烈看空（-80）
    - RSI >= 70：超买，看空（-40）
    - RSI >= 60：偏多（+30）
    - RSI >= 50：中性偏多（+20）
    - RSI >= 40：中性偏空（-20）
    - RSI >= 30：偏空（-30）
    - RSI >= 20：超卖，看多（+40）
    - RSI < 20：极度超卖，强烈看多（+60）

    注意：RSI超买时得分为负（看空），超卖时得分为正（看多），
    符合均值回归逻辑。

    Args:
        latest: 最新一行K线数据

    Returns:
        float: RSI因子得分，范围 -80 ~ +60
    """
    rsi = float(latest.get("RSI", 50)) if not pd.isna(latest.get("RSI")) else 50

    if rsi >= 80:
        return -80
    elif rsi >= 70:
        return -40
    elif rsi >= 60:
        return 30
    elif rsi >= 50:
        return 20
    elif rsi >= 40:
        return -20
    elif rsi >= 30:
        return -30
    elif rsi >= 20:
        return 40
    else:
        return 60


def _score_kdj(latest: pd.Series) -> float:
    """
    计算KDJ因子得分

    根据J值的区间映射评分：
    - J > 100：极度超买，强烈看空（-70）
    - J > 80：超买，看空（-40）
    - J > 60：偏多（+20）
    - J > 40：中性偏多（+10）
    - J > 20：偏空（+30，超卖反弹预期）
    - J > 0：超卖，看多（+40）
    - J <= 0：极度超卖，强烈看多（+50）

    注意：KDJ超买时得分为负（看空），超卖时得分为正（看多），
    符合均值回归逻辑。

    Args:
        latest: 最新一行K线数据

    Returns:
        float: KDJ因子得分，范围 -70 ~ +50
    """
    j_val = float(latest.get("J", 50)) if not pd.isna(latest.get("J")) else 50

    if j_val > 100:
        return -70
    elif j_val > 80:
        return -40
    elif j_val > 60:
        return 20
    elif j_val > 40:
        return 10
    elif j_val > 20:
        return 30
    elif j_val > 0:
        return 40
    else:
        return 50


def _score_bollinger(latest: pd.Series) -> float:
    """
    计算布林带因子得分

    根据价格在布林带中的位置（0=下轨，1=上轨）映射评分：
    - 位置 >= 1.0（触及或突破上轨）：超买看空（-60）
    - 位置 >= 0.85：偏上轨，偏空（-30）
    - 位置 >= 0.65：中上区域，偏多（+30）
    - 位置 >= 0.35：中间区域，中性偏多（+20）
    - 位置 >= 0.15：中下区域，偏多（+30）
    - 位置 < 0.15（触及或突破下轨）：超卖看多（+50）

    注意：布林带上轨附近得分为负（看空），下轨附近得分为正（看多），
    符合均值回归逻辑。

    Args:
        latest: 最新一行K线数据

    Returns:
        float: 布林带因子得分，范围 -60 ~ +50
    """
    close = float(latest["收盘"])
    bb_upper = float(latest.get("BB_UPPER", 0)) if not pd.isna(latest.get("BB_UPPER")) else 0
    bb_lower = float(latest.get("BB_LOWER", 0)) if not pd.isna(latest.get("BB_LOWER")) else 0
    bb_mid = float(latest.get("BB_MID", 0)) if not pd.isna(latest.get("BB_MID")) else 0

    # 布林带数据无效时返回中性得分
    if bb_upper <= 0 or bb_lower <= 0 or bb_mid <= 0:
        return 0

    band_width = bb_upper - bb_lower
    if band_width <= 0:
        return 0

    # 计算价格在布林带中的位置比例
    position = (close - bb_lower) / band_width

    if position >= 1.0:
        return -60
    elif position >= 0.85:
        return -30
    elif position >= 0.65:
        return 30
    elif position >= 0.35:
        return 20
    elif position >= 0.15:
        return 30
    else:
        return 50


def _score_volume(latest: pd.Series, df: pd.DataFrame) -> float:
    """
    计算成交量因子得分

    根据最新成交量与近5日平均成交量的比值（量比），
    结合涨跌幅方向评分：
    - 放量上涨（量比>2且涨跌幅>0）：强烈看多（+70）
    - 温和放量上涨（量比>1.5且涨跌幅>0）：偏多（+40）
    - 放量下跌（量比>2且涨跌幅<0）：强烈看空（-70）
    - 温和放量下跌（量比>1.5且涨跌幅<0）：偏空（-40）
    - 缩量（量比<0.5）：中性偏空（-10）
    - 其他：中性（0）

    Args:
        latest: 最新一行K线数据
        df: 完整K线历史数据

    Returns:
        float: 成交量因子得分，范围 -70 ~ +70
    """
    if len(df) < 5:
        return 0

    # 计算近5日平均成交量
    vol_series = df["成交量"].iloc[-5:]
    avg_vol = float(vol_series.mean())
    latest_vol = float(df["成交量"].iloc[-1])
    change_pct = float(latest.get("涨跌幅", 0))

    if avg_vol <= 0:
        return 0

    # 计算量比：最新成交量 / 平均成交量
    vol_ratio = latest_vol / avg_vol

    if vol_ratio > 2.0 and change_pct > 0:
        # 放量上涨
        return 70
    elif vol_ratio > 1.5 and change_pct > 0:
        # 温和放量上涨
        return 40
    elif vol_ratio > 2.0 and change_pct < 0:
        # 放量下跌
        return -70
    elif vol_ratio > 1.5 and change_pct < 0:
        # 温和放量下跌
        return -40
    elif vol_ratio < 0.5:
        # 缩量
        return -10
    else:
        return 0


def _score_fund_flow(latest: pd.Series) -> float:
    """
    计算资金流向因子得分

    根据累计净流入金额占收盘价的百分比评分：
    - 净流入占比 > 5%：强烈看多（+60）
    - 净流入占比 > 2%：偏多（+30）
    - 净流入占比 > 0%：中性偏多（+15）
    - 净流入占比 > -2%：中性偏空（-15）
    - 净流入占比 > -5%：偏空（-30）
    - 净流入占比 <= -5%：强烈看空（-60）

    Args:
        latest: 最新一行K线数据

    Returns:
        float: 资金流向因子得分，范围 -60 ~ +60
    """
    cum_flow = float(latest.get("累计净流入", 0)) if not pd.isna(latest.get("累计净流入")) else 0
    close = float(latest["收盘"])

    if close <= 0:
        return 0

    # 计算净流入金额占收盘价的百分比
    flow_pct = cum_flow / close * 100

    if flow_pct > 5:
        return 60
    elif flow_pct > 2:
        return 30
    elif flow_pct > 0:
        return 15
    elif flow_pct > -2:
        return -15
    elif flow_pct > -5:
        return -30
    else:
        return -60


def _score_volatility(latest: pd.Series, df: pd.DataFrame) -> float:
    """
    计算波动率因子得分

    根据ATR（平均真实波幅）占收盘价的百分比评分：
    - ATR占比 > 3%：高波动，风险大（-50）
    - ATR占比 > 2%：较高波动（-20）
    - ATR占比 > 1%：正常波动（+10）
    - ATR占比 > 0.5%：低波动，稳定（+20）
    - ATR占比 <= 0.5%：极低波动（+30）

    高波动通常意味着市场不确定性增加，得分为负；
    低波动通常意味着市场稳定，得分为正。

    Args:
        latest: 最新一行K线数据
        df: 完整K线历史数据

    Returns:
        float: 波动率因子得分，范围 -50 ~ +30
    """
    atr = float(latest.get("ATR", 0)) if not pd.isna(latest.get("ATR")) else 0
    close = float(latest["收盘"])

    if close <= 0 or atr <= 0:
        return 0

    # 计算ATR占收盘价的百分比
    atr_pct = atr / close * 100

    if atr_pct > 3.0:
        return -50
    elif atr_pct > 2.0:
        return -20
    elif atr_pct > 1.0:
        return 10
    elif atr_pct > 0.5:
        return 20
    else:
        return 30


def calc_composite_score(latest: pd.Series, df: pd.DataFrame,
                         weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    计算多因子综合评分

    将8个技术因子（均线趋势、MACD、RSI、KDJ、布林带、成交量、资金流向、波动率）
    按各自权重加权求和，得到综合评分，并根据评分映射市场状态和交易信号。

    Args:
        latest: 最新一行K线数据
        df: 完整K线历史数据
        weights: 自定义因子权重字典，为None时使用默认权重 FACTOR_WEIGHTS

    Returns:
        dict: 综合评分结果，包含以下字段：
            - score (float): 综合评分，范围 -100 ~ +100
            - market_state (str): 市场状态英文标识
                strong_bull / bull / neutral / bear / strong_bear
            - market_state_cn (str): 市场状态中文描述
                强势上涨 / 震荡偏多 / 中性 / 震荡偏空 / 弱势下跌
            - factors (dict): 各因子得分详情
            - signal (str): 交易信号，买入 / 卖出 / 观望
            - position_suggestion (float): 建议仓位比例，范围 0.0 ~ 1.0
    """
    w = weights or FACTOR_WEIGHTS

    # 计算各因子得分
    factor_scores = {
        "ma_trend": _score_ma_trend(latest, df),
        "macd": _score_macd(latest, df),
        "rsi": _score_rsi(latest),
        "kdj": _score_kdj(latest),
        "bollinger": _score_bollinger(latest),
        "volume": _score_volume(latest, df),
        "fund_flow": _score_fund_flow(latest),
        "volatility": _score_volatility(latest, df),
    }

    # 按权重加权求和计算综合评分
    score = 0.0
    for factor_name, factor_score in factor_scores.items():
        weight = w.get(factor_name, 0)
        score += factor_score * weight

    # 将综合评分限制在 -100 ~ +100 范围内
    score = max(-100, min(100, round(score, 2)))

    # 根据综合评分映射市场状态
    if score >= 50:
        market_state = "strong_bull"
        market_state_cn = "强势上涨"
    elif score >= 20:
        market_state = "bull"
        market_state_cn = "震荡偏多"
    elif score >= -20:
        market_state = "neutral"
        market_state_cn = "中性"
    elif score >= -50:
        market_state = "bear"
        market_state_cn = "震荡偏空"
    else:
        market_state = "strong_bear"
        market_state_cn = "弱势下跌"

    # 根据综合评分映射交易信号
    if score >= 30:
        signal = "买入"
    elif score <= -30:
        signal = "卖出"
    else:
        signal = "观望"

    # 根据综合评分映射建议仓位比例
    if score >= 60:
        position_suggestion = 0.9
    elif score >= 40:
        position_suggestion = 0.7
    elif score >= 20:
        position_suggestion = 0.5
    elif score >= 0:
        position_suggestion = 0.3
    elif score >= -20:
        position_suggestion = 0.2
    elif score >= -40:
        position_suggestion = 0.1
    else:
        position_suggestion = 0.0

    return {
        "score": score,
        "market_state": market_state,
        "market_state_cn": market_state_cn,
        "factors": factor_scores,
        "signal": signal,
        "position_suggestion": position_suggestion,
    }


def get_recommended_strategy(score: float) -> str:
    """
    根据综合评分推荐最佳策略

    不同市场环境下适合不同的交易策略：
    - 评分 >= 40（强势多头）：推荐 ma_trend 趋势策略，顺势而为
    - 评分 >= 20（震荡偏多）：推荐 grid 网格策略，区间操作
    - 评分 <= -40（强势空头）：推荐 ma_trend 趋势策略，顺势做空
    - 评分 <= -20（震荡偏空）：推荐 bollinger 布林带策略，均值回归
    - 其他（中性）：推荐 grid 网格策略，稳健操作

    Args:
        score: 多因子综合评分，范围 -100 ~ +100

    Returns:
        str: 推荐的策略名称，取值为 grid / ma_trend / bollinger / rsi / macd_cross
    """
    if score >= 40:
        return "ma_trend"
    elif score >= 20:
        return "grid"
    elif score <= -40:
        return "ma_trend"
    elif score <= -20:
        return "bollinger"
    else:
        return "grid"
