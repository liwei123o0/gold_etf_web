"""Simulation Trading Service - SQLite persistence"""
import uuid
from datetime import datetime
from backend.models.simulation import (
    SimulationAccount,
    SimulationPosition,
    SimulationOrder,
)
from backend.models.settings import SimSettings

def reset_portfolio(user_id, initial_capital):
    """Reset account: delete all data and create new account"""
    SimulationAccount.delete_by_user_id(user_id)
    SimulationPosition.delete_by_user_id(user_id)
    SimulationOrder.delete_by_user_id(user_id)
    SimulationAccount.upsert(user_id, initial_capital, initial_capital)
    return get_portfolio(user_id)

def get_portfolio(user_id):
    """Get full portfolio from SQLite"""
    account = SimulationAccount.find_by_user_id(user_id)
    if account is None:
        return None
    positions = SimulationPosition.find_by_user_id(user_id)
    orders = SimulationOrder.find_by_user_id(user_id)
    market_value = sum(p["shares"] * p["current_price"] for p in positions)
    unrealized = sum(p["unrealized_pnl"] for p in positions)
    account["market_value"] = market_value
    account["unrealized_pnl"] = unrealized
    account["total_assets"] = account["cash"] + market_value
    account["total_pnl"] = account["realized_pnl"] + unrealized
    total_return = account["total_assets"] - account["initial_capital"]
    total_return_pct = (total_return / account["initial_capital"] * 100) if account["initial_capital"] else 0
    return {
        "account": account,
        "positions": positions,
        "orders": orders,
        "total_return": total_return,
        "total_return_pct": total_return_pct,
    }

def place_order(user_id, direction, symbol, name, price, shares, commission, pnl=0, trade_type="manual"):
    """Insert order record"""
    order_id = str(uuid.uuid4())[:8]
    SimulationOrder.insert(order_id, user_id, direction, symbol, name, price, shares, commission, pnl, trade_type)
    return {
        "id": order_id,
        "direction": direction,
        "symbol": symbol,
        "name": name,
        "price": price,
        "shares": shares,
        "commission": commission,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pnl": pnl,
        "trade_type": trade_type,
    }

def execute_trade(user_id, direction, symbol, name, price, shares, trade_type="manual"):
    """Execute buy or sell trade with SQLite persistence"""
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return {"success": False, "error": "Account not found, please reset"}

    account = portfolio["account"]
    settings = SimSettings.get(symbol)
    amount = price * shares

    # Calculate commission using settings
    commission = max(amount * settings["commission_rate"], settings["min_commission"])

    if direction == "buy":
        total_cost = amount + commission
        if account["cash"] < total_cost:
            return {"success": False, "error": f"Insufficient funds, need {total_cost:.2f}, available {account['cash']:.2f}"}

        pos = next((p for p in portfolio["positions"] if p["symbol"] == symbol), None)
        if pos:
            total_cost_shares = pos["shares"] * pos["avg_cost"] + amount
            new_shares = pos["shares"] + shares
            new_avg_cost = total_cost_shares / new_shares
        else:
            new_shares = shares
            new_avg_cost = price

        new_cash = account["cash"] - total_cost
        SimulationAccount.upsert(user_id, account["initial_capital"], new_cash, 0.0, account["realized_pnl"])
        SimulationPosition.upsert(user_id, symbol, name, new_shares, new_avg_cost, price)
        order = place_order(user_id, "buy", symbol, name, price, shares, commission, trade_type=trade_type)
        return {"success": True, "order": order, "portfolio": get_portfolio(user_id)}

    elif direction == "sell":
        pos = next((p for p in portfolio["positions"] if p["symbol"] == symbol), None)
        if not pos or pos["shares"] < shares:
            return {"success": False, "error": "Insufficient position"}

        # Calculate fees using settings
        stamp_tax = amount * settings["stamp_tax_rate"]  # seller only
        transfer_fee = amount * settings["transfer_fee_rate"] if symbol.startswith("sh") else 0
        total_fees = commission + stamp_tax + transfer_fee
        net_amount = amount - total_fees

        realized_pnl = (price - pos["avg_cost"]) * shares - total_fees
        new_cash = account["cash"] + net_amount
        new_realized_pnl = account["realized_pnl"] + realized_pnl
        SimulationAccount.upsert(user_id, account["initial_capital"], new_cash, 0.0, new_realized_pnl)

        new_shares = pos["shares"] - shares
        SimulationPosition.upsert(user_id, symbol, name, new_shares, pos["avg_cost"], price)

        order = place_order(user_id, "sell", symbol, name, price, shares, total_fees, realized_pnl, trade_type)
        return {"success": True, "order": order, "portfolio": get_portfolio(user_id)}

    return {"success": False, "error": "Invalid direction"}

def close_all_positions(user_id):
    """Close all positions"""
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return {"success": False, "error": "Account not found"}
    closed = []
    for pos in list(portfolio["positions"]):
        result = execute_trade(user_id, "sell", pos["symbol"], pos["name"], pos["current_price"], pos["shares"])
        if result["success"]:
            closed.append(pos)
    return {"success": True, "closed": closed, "portfolio": get_portfolio(user_id)}

def clear_orders(user_id):
    """Clear all order history for user"""
    SimulationOrder.delete_by_user_id(user_id)
    return {"success": True}

def update_prices(user_id, realtime_map):
    """Update current prices for positions"""
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return None
    for pos in portfolio["positions"]:
        rt = realtime_map.get(pos["symbol"])
        if rt:
            SimulationPosition.upsert(user_id, pos["symbol"], pos["name"], pos["shares"], pos["avg_cost"], rt["price"])
    return get_portfolio(user_id)
