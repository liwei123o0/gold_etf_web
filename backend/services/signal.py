"""
信号监控服务

提供技术分析信号的生成、评估和格式化。
支持多标的（黄金ETF、沪深300等），生成可用于提醒的信号摘要。
"""

import pandas as pd
from typing import Dict, Any, List, Optional
from backend.services.gold_data import (
    get_full_data,
    generate_signals,
    STOCK_NAMES,
    DEFAULT_SYMBOL,
)


class SignalSummary:
    """信号摘要（可序列化）"""

    def __init__(self, symbol: str, data: Dict[str, Any]):
        self.symbol = symbol
        self.name = STOCK_NAMES.get(symbol, symbol.upper())
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "close": self.data.get("收盘", 0),
            "change_pct": self.data.get("涨跌幅", 0),
            "rsi": self.data.get("RSI", 0),
            "j": self.data.get("J", 0),
            "macd_hist": self.data.get("MACD_HIST", 0),
            "ma5": self.data.get("MA5", 0),
            "ma10": self.data.get("MA10", 0),
            "ma20": self.data.get("MA20", 0),
            "signals": self.data.get("signals", []),
        }


def get_signal_summary(symbol: str = DEFAULT_SYMBOL, datalen: int = 60) -> SignalSummary:
    """
    获取指定标的的信号摘要。

    Parameters
    ----------
    symbol : str
        股票代码，如 sh518880、sz000300
    datalen : int
        数据天数，默认60天（足够计算MA20和更准确的指标）

    Returns
    -------
    SignalSummary
        包含最新数据和技术分析信号的摘要对象
    """
    df = get_full_data(symbol=symbol, datalen=datalen)
    latest = df.iloc[-1]
    signals = generate_signals(latest)

    data = {
        "收盘": float(latest["收盘"]) if not pd.isna(latest["收盘"]) else 0,
        "涨跌幅": float(latest["涨跌幅"]) if not pd.isna(latest["涨跌幅"]) else 0,
        "MA5": float(latest["MA5"]) if not pd.isna(latest["MA5"]) else 0,
        "MA10": float(latest["MA10"]) if not pd.isna(latest["MA10"]) else 0,
        "MA20": float(latest["MA20"]) if not pd.isna(latest["MA20"]) else 0,
        "RSI": float(latest["RSI"]) if not pd.isna(latest["RSI"]) else 0,
        "J": float(latest["J"]) if not pd.isna(latest["J"]) else 0,
        "MACD": float(latest["MACD"]) if not pd.isna(latest["MACD"]) else 0,
        "MACD_SIGNAL": float(latest["MACD_SIGNAL"]) if not pd.isna(latest["MACD_SIGNAL"]) else 0,
        "MACD_HIST": float(latest["MACD_HIST"]) if not pd.isna(latest["MACD_HIST"]) else 0,
        "累计净流入": float(latest["累计净流入"]) if not pd.isna(latest["累计净流入"]) else 0,
        "signals": signals,
    }

    return SignalSummary(symbol, data)


def format_signal_text(summary: SignalSummary) -> str:
    """
    将信号摘要格式化为易读的文本（用于微信公众号）。

    Returns
    -------
    str
        格式化后的文本内容
    """
    d = summary.to_dict()
    lines = []

    # 标题区
    lines.append(f"📊 {d['name']}（{d['symbol'].upper()}）技术信号")
    lines.append("")

    # 价格信息
    change_emoji = "🔴" if d["change_pct"] < 0 else "🟢"
    lines.append(f"💵 最新价：{d['close']:.4f}  {change_emoji} {d['change_pct']:+.2f}%")
    lines.append("")

    # 关键指标
    lines.append("📈 关键指标")
    lines.append(f"  • MA5:  {d['ma5']:.4f}")
    lines.append(f"  • MA10: {d['ma10']:.4f}")
    lines.append(f"  • MA20: {d['ma20']:.4f}")
    lines.append(f"  • RSI:  {d['rsi']:.1f}")
    lines.append(f"  • KDJ-J:{d['j']:.1f}")
    lines.append(f"  • MACD柱: {d['macd_hist']:.4f}")
    lines.append("")

    # 信号区
    lines.append("🎯 综合信号")
    bullish = []
    bearish = []
    neutral = []

    for name, status, desc in d["signals"]:
        if "✅" in status or "📈" in status:
            bullish.append((name, status, desc))
        elif "⚠️" in status:
            bearish.append((name, status, desc))
        else:
            neutral.append((name, status, desc))

    if bullish:
        lines.append("  【利好信号】")
        for name, status, desc in bullish:
            lines.append(f"  {status} {name}：{desc}")

    if bearish:
        lines.append("  【警示信号】")
        for name, status, desc in bearish:
            lines.append(f"  {status} {name}：{desc}")

    if neutral:
        lines.append("  【中性信号】")
        for name, status, desc in neutral:
            lines.append(f"  {status} {name}：{desc}")

    lines.append("")
    lines.append("⚠️ 免责声明：本分析仅基于历史数据技术分析，不构成投资建议。投资有风险，入市需谨慎。")

    return "\n".join(lines)


def get_trading_signal(summary: SignalSummary) -> str:
    """
    返回简化的交易信号（买入/卖出/观望）。

    Returns
    -------
    str
        "买入" / "卖出" / "观望"
    """
    d = summary.to_dict()
    score = 0

    # 均线多头+1，空头-1
    if d["close"] > d["ma5"] and d["ma5"] > d["ma10"]:
        score += 1
    elif d["close"] < d["ma5"] and d["ma5"] < d["ma10"]:
        score -= 1

    # MACD柱>0 +1
    if d["macd_hist"] > 0:
        score += 1
    elif d["macd_hist"] < 0:
        score -= 1

    # RSI 30-70正常，>70超买-1，<30超卖+1
    if d["rsi"] > 70:
        score -= 1
    elif d["rsi"] < 30:
        score += 1

    # KDJ J>80超买-1，<20超卖+1
    if d["j"] > 80:
        score -= 1
    elif d["j"] < 20:
        score += 1

    if score >= 2:
        return "买入"
    elif score <= -2:
        return "卖出"
    else:
        return "观望"
