
"""
Sim Trading Service
"""
import uuid
from datetime import datetime
from typing import Optional, Dict

_portfolios = {}

def reset_portfolio(user_id, initial_capital):
    account = {
        "initial_capital": initial_capital,
        "cash": initial_capital,
        "frozen_cash": 0.0,
        "market_value": 0.0,
        "total_assets": initial_capital,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "total_pnl": 0.0
    }
    portfolio = {"account": account, "positions": [], "orders": [], "total_return": 0.0, "total_return_pct": 0.0}
    _portfolios[user_id] = portfolio
    return portfolio

def get_portfolio(user_id):
    return _portfolios.get(user_id)

def place_order(user_id, direction, symbol, name, price, shares, commission, pnl=0):
    portfolio = _portfolios.get(user_id)
    if not portfolio:
        return None
    order = {
        "id": str(uuid.uuid4())[:8],
        "direction": direction,
        "symbol": symbol,
        "name": name,
        "price": price,
        "shares": shares,
        "commission": commission,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pnl": pnl
    }
    portfolio["orders"].insert(0, order)
    return order

def update_prices(user_id, realtime_map):
    portfolio = _portfolios.get(user_id)
    if not portfolio:
        return None
    unrealized_pnl = 0.0
    for p in portfolio["positions"]:
        rt = realtime_map.get(p["symbol"])
        if rt:
            p["current_price"] = rt.get("price", p["current_price"])
        p["unrealized_pnl"] = (p["current_price"] - p["avg_cost"]) * p["shares"]
        p["unrealized_pnl_pct"] = (p["current_price"] - p["avg_cost"]) / p["avg_cost"] * 100 if p["avg_cost"] else 0
        unrealized_pnl += p["unrealized_pnl"]
    portfolio["account"]["unrealized_pnl"] = unrealized_pnl
    portfolio["account"]["market_value"] = sum(p["shares"] * p["current_price"] for p in portfolio["positions"])
    portfolio["account"]["total_assets"] = portfolio["account"]["cash"] + portfolio["account"]["market_value"]
    ta = portfolio["account"]["total_assets"]
    ic = portfolio["account"]["initial_capital"]
    portfolio["total_return"] = ta - ic
    portfolio["total_return_pct"] = (ta - ic) / ic * 100 if ic else 0
    return portfolio

def execute_trade(user_id, direction, symbol, name, price, shares):
    """执行买卖交易"""
    portfolio = _portfolios.get(user_id)
    if not portfolio:
        return {"success": False, "error": "账户不存在，请先重置"}
    
    account = portfolio["account"]
    
    # 计算手续费
    amount = price * shares
    commission = max(amount * 0.0003, 5)  # 佣金0.03%，最低5元
    
    if direction == "buy":
        total_cost = amount + commission
        if account["cash"] < total_cost:
            return {"success": False, "error": f"资金不足，需要 {total_cost:.2f} 元，可用 {account['cash']:.2f} 元"}
        
        # 扣除资金
        account["cash"] -= total_cost
        
        # 查找或创建持仓
        pos = next((p for p in portfolio["positions"] if p["symbol"] == symbol), None)
        if pos:
            total_cost_shares = pos["shares"] * pos["avg_cost"] + amount
            pos["shares"] += shares
            pos["avg_cost"] = total_cost_shares / pos["shares"]
            pos["current_price"] = price
            pos["unrealized_pnl"] = (price - pos["avg_cost"]) * pos["shares"]
            pos["unrealized_pnl_pct"] = (price - pos["avg_cost"]) / pos["avg_cost"] * 100 if pos["avg_cost"] else 0
        else:
            portfolio["positions"].append({
                "symbol": symbol,
                "name": name,
                "shares": shares,
                "avg_cost": price,
                "current_price": price,
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0
            })
        
        order = place_order(user_id, "buy", symbol, name, price, shares, commission)
        # 更新账户统计
        portfolio["account"]["market_value"] = sum(p["shares"] * p["current_price"] for p in portfolio["positions"])
        unrealized = sum((p["current_price"] - p["avg_cost"]) * p["shares"] for p in portfolio["positions"])
        portfolio["account"]["unrealized_pnl"] = unrealized
        portfolio["account"]["total_assets"] = portfolio["account"]["cash"] + portfolio["account"]["market_value"]
        ta = portfolio["account"]["total_assets"]
        ic = portfolio["account"]["initial_capital"]
        portfolio["account"]["total_pnl"] = portfolio["account"]["realized_pnl"] + unrealized
        portfolio["account"]["total_return_pct"] = (ta - ic) / ic * 100 if ic else 0
        return {"success": True, "order": order, "portfolio": portfolio}
    
    elif direction == "sell":
        pos = next((p for p in portfolio["positions"] if p["symbol"] == symbol), None)
        if not pos or pos["shares"] < shares:
            return {"success": False, "error": "持仓不足"}
        
        # 印花税0.1%（仅卖方）
        stamp_tax = amount * 0.001
        # 过户费0.002%（仅上海）
        transfer_fee = amount * 0.00002 if symbol.startswith("sh") else 0
        total_fees = commission + stamp_tax + transfer_fee
        net_amount = amount - total_fees
        
        # 增加资金
        account["cash"] += net_amount
        
        # 更新持仓
        pos["shares"] -= shares
        realized_pnl = (price - pos["avg_cost"]) * shares - total_fees
        
        if pos["shares"] == 0:
            portfolio["positions"].remove(pos)
        
        order = place_order(user_id, "sell", symbol, name, price, shares, total_fees, realized_pnl)
        account["realized_pnl"] += realized_pnl
        # 更新账户统计
        account["market_value"] = sum(p["shares"] * p["current_price"] for p in portfolio["positions"])
        account["total_assets"] = account["cash"] + account["market_value"]
        unrealized = sum((p["current_price"] - p["avg_cost"]) * p["shares"] for p in portfolio["positions"])
        account["unrealized_pnl"] = unrealized
        account["total_pnl"] = account["realized_pnl"] + unrealized
        ta = account["total_assets"]
        ic = account["initial_capital"]
        account["total_return_pct"] = (ta - ic) / ic * 100 if ic else 0
        return {"success": True, "order": order, "portfolio": portfolio}
    
    return {"success": False, "error": "无效的交易方向"}

def close_all_positions(user_id):
    """清仓"""
    portfolio = _portfolios.get(user_id)
    if not portfolio:
        return {"success": False, "error": "账户不存在"}
    
    closed = []
    for pos in list(portfolio["positions"]):
        result = execute_trade(user_id, "sell", pos["symbol"], pos["name"], pos["current_price"], pos["shares"])
        if result["success"]:
            closed.append(pos)
    
    return {"success": True, "closed": closed, "portfolio": portfolio}
