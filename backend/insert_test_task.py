"""插入自动交易任务初始数据"""
import sys
sys.path.insert(0, '.')

from backend.models.auto_trade import AutoTradeTask
from backend.utils.timezone import china_now_naive
from backend.utils.symbol import normalize_symbol

symbol = normalize_symbol("515880")
print(f"规范化的股票代码: {symbol}")

position_shares = 7200
position_avg_cost = 1.419
current_price = 1.430

position_value = position_shares * position_avg_cost
available_cash = 2000.0
allocated_funds = position_value + available_cash
unrealized_pnl = (current_price - position_avg_cost) * position_shares

print(f"持仓市值: {position_value:.2f}")
print(f"剩余可用资金: {available_cash:.2f}")
print(f"分配总资金: {allocated_funds:.2f}")
print(f"浮动盈亏: {unrealized_pnl:.2f}")

try:
    task_data = {
        "user_id": 3,
        "symbol": symbol,
        "strategy": "grid",
        "grid_count": 10,
        "grid_spread": 0.10,
        "base_ma_key": "MA20",
        "allocated_funds": allocated_funds,
        "enabled": False,
        "task_name": "黄金ETF",
        "position_shares": position_shares,
        "position_avg_cost": position_avg_cost,
        "task_cash": available_cash,
        "task_pnl": 0,
        "unrealized_pnl": unrealized_pnl,
        "stop_loss_pct": -5.0,
        "take_profit_pct": 10.0,
        "trend_ma_key": None,
        "dynamic_interval": False,
        "trade_count_today": 0,
    }
    
    AutoTradeTask.create_or_update(task_data)
    print("数据插入成功！")
except Exception as e:
    print(f"插入失败: {e}")
    import traceback
    traceback.print_exc()
