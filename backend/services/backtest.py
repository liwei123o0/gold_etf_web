"""
网格交易回测服务

提供历史数据回测功能，计算网格交易策略的绩效指标。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from backend.services.grid_trade import calc_grid_params, DEFAULT_GRID_COUNT, DEFAULT_GRID_SPREAD


def run_grid_backtest(
    df: pd.DataFrame,
    initial_capital: float = 100000.0,
    grid_count: int = DEFAULT_GRID_COUNT,
    spread_type: str = "fixed",
    base_ma_key: str = "MA20",
    position_size: float = 1.0
) -> Dict[str, Any]:
    """
    运行网格交易回测。

    Parameters
    ----------
    df : pd.DataFrame
        历史数据，需包含：日期, 收盘, MA5, MA10, MA20, MA60, ATR 等列
    initial_capital : float
        初始资金（元），默认 100000
    grid_count : int
        网格格数，默认 10
    spread_type : str
        "fixed" = 固定 ±5% 区间，"atr" = ATR 动态区间
    base_ma_key : str
        基准均线字段名：MA5 / MA10 / MA20 / MA60
    position_size : float
        每次交易资金占比（0.0-1.0），默认 1.0 全仓

    Returns
    -------
    Dict
        回测结果，包含资金曲线、交易记录、绩效指标
    """
    # 复制避免修改原始数据
    data = df.copy().reset_index(drop=True)

    # 预热期：根据基准均线动态确定
    if base_ma_key == "MA60":
        warmup = 65  # MA60 需要 60 天 + buffer
    elif base_ma_key == "MA20":
        warmup = 25  # MA20 需要 20 天 + buffer
    elif base_ma_key == "MA10":
        warmup = 15
    else:
        warmup = 10  # MA5

    if len(data) <= warmup:
        return _empty_result(initial_capital, f"数据不足，当前{len(data)}天数据需要至少{warmup}天")

    # 过滤预热期
    data = data.iloc[warmup:].reset_index(drop=True)

    # 初始状态
    cash = initial_capital
    shares = 0
    position_ratio = 0.0

    # 权益曲线
    equity_curve: List[Dict[str, Any]] = []

    # 交易记录
    trade_history: List[Dict[str, Any]] = []

    # 当前持仓信息
    entry_price = 0.0
    entry_grid = 0
    entry_date = ""

    # 上一个网格索引
    prev_grid_idx = None

    for i in range(len(data)):
        row = data.iloc[i]
        close = float(row['收盘'])
        date_str = str(row['日期'])
        ma_val = float(row.get(base_ma_key, close))
        atr = float(row.get('ATR', 0))

        # 计算网格参数
        if spread_type == "atr" and atr > 0:
            # ATR 动态区间：总幅度 = 4×ATR / base_price，限制 5%~30%
            spread_raw = (4 * atr) / ma_val if ma_val > 0 else DEFAULT_GRID_SPREAD
            spread = max(0.05, min(0.30, spread_raw))
        else:
            spread = DEFAULT_GRID_SPREAD

        # 计算网格上下界
        half = spread / 2
        lower_price = ma_val * (1 - half)
        upper_price = ma_val * (1 + half)

        # 网格价格数组
        grid_prices = np.linspace(lower_price, upper_price, grid_count + 1)

        # 当前价格所在网格索引
        grid_idx = int(np.searchsorted(grid_prices, close))
        grid_idx = min(max(grid_idx, 0), grid_count)

        # 当日权益
        equity = cash + shares * close
        equity_curve.append({"date": date_str, "equity": round(equity, 2)})

        # 网格边界穿越判断
        if prev_grid_idx is not None:
            # 价格上涨（网格索引减小 = 向上走）
            # 价格下跌（网格索引增大 = 向下走）

            if shares == 0 and grid_idx <= prev_grid_idx - 1:
                # 无持仓 + 价格跌破下边界 → 买入
                buy_amount = cash * position_size
                if buy_amount > 0 and close > 0:
                    new_shares = int(buy_amount / close)
                    if new_shares > 0:
                        entry_price = close
                        entry_grid = grid_idx
                        entry_date = date_str
                        shares = new_shares
                        cash -= new_shares * close

            elif shares > 0 and grid_idx >= prev_grid_idx + 1:
                # 有持仓 + 价格涨破上边界 → 卖出
                exit_price = close
                exit_grid = grid_idx
                exit_date = date_str
                pnl = (exit_price - entry_price) * shares
                pnl_pct = (exit_price - entry_price) / entry_price * 100 if entry_price > 0 else 0

                trade_history.append({
                    "entry_date": entry_date,
                    "entry_price": round(entry_price, 4),
                    "entry_grid": entry_grid,
                    "exit_date": exit_date,
                    "exit_price": round(exit_price, 4),
                    "exit_grid": exit_grid,
                    "shares": shares,
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                })

                cash += shares * exit_price
                shares = 0

        prev_grid_idx = grid_idx

    # 最终权益
    final_equity = cash + shares * float(data.iloc[-1]['收盘'])

    # 绩效计算
    total_return = final_equity - initial_capital
    total_return_pct = total_return / initial_capital * 100 if initial_capital > 0 else 0

    # 最大回撤
    max_drawdown, peak = 0.0, initial_capital
    for point in equity_curve:
        if point["equity"] > peak:
            peak = point["equity"]
        dd = (peak - point["equity"]) / peak * 100 if peak > 0 else 0
        if dd > max_drawdown:
            max_drawdown = dd

    # 胜率
    if trade_history:
        num_wins = sum(1 for t in trade_history if t["pnl"] > 0)
        win_rate = num_wins / len(trade_history) * 100
    else:
        num_wins = 0
        win_rate = 0.0

    return {
        "initial_capital": initial_capital,
        "final_equity": round(final_equity, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2),
        "num_trades": len(trade_history),
        "num_wins": num_wins,
        "win_rate": round(win_rate, 1),
        "max_drawdown_pct": round(max_drawdown, 2),
        "equity_curve": equity_curve,
        "trade_history": trade_history,
        "params": {
            "grid_count": grid_count,
            "spread_type": spread_type,
            "base_ma_key": base_ma_key,
            "position_size": position_size,
            "warmup_days": warmup,
        }
    }


def _empty_result(initial_capital: float, reason: str) -> Dict[str, Any]:
    """返回空结果的辅助函数"""
    return {
        "initial_capital": initial_capital,
        "final_equity": initial_capital,
        "total_return": 0,
        "total_return_pct": 0,
        "num_trades": 0,
        "num_wins": 0,
        "win_rate": 0,
        "max_drawdown_pct": 0,
        "equity_curve": [],
        "trade_history": [],
        "params": {},
        "reason": reason,
    }
