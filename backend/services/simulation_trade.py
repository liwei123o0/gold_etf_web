"""
模拟交易服务模块 - 基于 PostgreSQL (SQLAlchemy ORM) 持久化

本模块提供模拟交易的核心功能，包括：
- 账户管理：重置账户、获取账户信息
- 持仓管理：买入、卖出、清仓
- 订单管理：下单、成交记录
- 自动交易任务聚合：将自动交易任务的持仓和盈亏汇总到账户视图
"""
import uuid
import logging
from datetime import datetime
from typing import Dict

from backend.models.db import get_session
from backend.models.simulation import (
    SimulationAccount,
    SimulationPosition,
    SimulationOrder,
)
from backend.models.settings import SimSettings

logger = logging.getLogger(__name__)


def reset_portfolio(user_id, initial_capital):
    """
    重置模拟账户
    
    删除用户的所有模拟交易数据（账户、持仓、订单），并创建新的账户。
    
    Args:
        user_id: 用户ID
        initial_capital: 初始资金金额
        
    Returns:
        dict: 重置后的账户信息（包含账户、持仓、订单等）
    """
    SimulationAccount.delete_by_user_id(user_id)
    SimulationPosition.delete_by_user_id(user_id)
    SimulationOrder.delete_by_user_id(user_id)
    SimulationAccount.upsert(user_id, initial_capital, initial_capital)
    return get_portfolio(user_id)


def get_portfolio(user_id):
    """
    获取用户的完整账户信息
    
    从数据库获取用户的账户、持仓、订单信息，并聚合自动交易任务的数据。
    自动交易任务的持仓市值和浮动盈亏会被合并到账户总计中。
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 包含以下字段的账户信息字典
            - account: 账户信息（资金、市值、盈亏等）
            - positions: 持仓列表
            - orders: 订单列表
            - auto_tasks: 自动交易任务汇总
            - total_return: 总收益金额
            - total_return_pct: 总收益率百分比
    """
    account = SimulationAccount.find_by_user_id(user_id)
    if account is None:
        return None
    positions = SimulationPosition.find_by_user_id(user_id)
    orders = SimulationOrder.find_by_user_id(user_id)
    
    # 计算手动持仓的市值和浮动盈亏
    manual_market_value = sum(p["shares"] * p["current_price"] for p in positions)
    manual_unrealized = sum(p["unrealized_pnl"] for p in positions)

    # 获取自动交易任务的汇总数据
    auto_tasks_summary = _get_auto_tasks_summary(user_id)

    # 合并手动持仓和自动交易任务的数据
    total_market_value = manual_market_value + auto_tasks_summary["market_value"]
    total_unrealized = manual_unrealized + auto_tasks_summary["unrealized_pnl"]
    total_realized = account["realized_pnl"] + auto_tasks_summary["realized_pnl"]

    # 更新账户汇总信息
    account["market_value"] = total_market_value
    account["unrealized_pnl"] = total_unrealized
    account["total_assets"] = account["cash"] + total_market_value
    account["total_pnl"] = total_realized + total_unrealized
    total_return = account["total_assets"] - account["initial_capital"]
    total_return_pct = (total_return / account["initial_capital"] * 100) if account["initial_capital"] else 0
    
    return {
        "account": account,
        "positions": positions,
        "orders": orders,
        "auto_tasks": auto_tasks_summary,
        "total_return": total_return,
        "total_return_pct": total_return_pct,
    }


def _get_auto_tasks_summary(user_id):
    """
    聚合用户所有自动交易任务的持仓和盈亏数据
    
    遍历用户的所有自动交易任务，获取实时价格，计算每个任务的市值和浮动盈亏，
    并汇总返回。
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 包含以下字段的汇总信息
            - task_count: 任务数量
            - market_value: 总市值
            - unrealized_pnl: 总浮动盈亏
            - realized_pnl: 总已实现盈亏
            - tasks: 任务详情列表
    """
    empty_result = {
        "task_count": 0,
        "market_value": 0.0,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "tasks": [],
    }

    # 尝试通过 ORM 查询自动交易任务
    try:
        from backend.models.auto_trade import AutoTradeTask
        tasks = AutoTradeTask.find_by_user(user_id)
        logger.info(f"[Portfolio] AutoTradeTask.find_by_user({user_id}) returned {len(tasks)} tasks")
    except Exception as e:
        # ORM 查询失败时，尝试直接 SQL 查询作为兜底
        logger.warning(f"[Portfolio] AutoTradeTask ORM query failed: {e}, trying SQL fallback")
        try:
            tasks = _query_auto_tasks_sql(user_id)
            logger.info(f"[Portfolio] SQL fallback returned {len(tasks)} tasks")
        except Exception as e2:
            logger.error(f"[Portfolio] Both ORM and SQL fallback failed for user_id={user_id}: {e2}")
            return empty_result

    if not tasks:
        return empty_result

    # 获取所有任务涉及的股票代码，批量查询实时价格
    all_symbols = list({t.get("symbol", "") for t in tasks if t.get("symbol")})
    realtime_prices: Dict[str, float] = {}
    try:
        from backend.routes.realtime import get_realtime
        from backend.utils.symbol import strip_prefix
        sym_str = ",".join(all_symbols)
        result = get_realtime(sym_str)
        if result.get("code") == 0 and result.get("data"):
            data = result["data"]
            for sym, item in data.items():
                realtime_prices[sym] = float(item.get("price", 0) or 0)
                # 同时存储去掉前缀的代码，方便后续匹配
                alt = strip_prefix(sym)
                if alt != sym:
                    realtime_prices[alt] = realtime_prices[sym]
    except Exception as e:
        logger.warning(f"[Portfolio] Failed to fetch realtime prices for auto tasks: {e}")

    task_list = []
    market_value = 0.0
    unrealized_pnl = 0.0
    realized_pnl = 0.0

    # 遍历每个任务，计算市值和浮动盈亏
    for t in tasks:
        shares = int(t.get("position_shares", 0) or 0)
        avg_cost = float(t.get("position_avg_cost", 0) or 0)
        allocated = float(t.get("allocated_funds", 0) or 0)
        task_pnl = float(t.get("task_pnl", 0) or 0)
        stored_unrealized = float(t.get("unrealized_pnl", 0) or 0)
        symbol = t.get("symbol", "")

        # 获取实时价格，优先使用实时价格，其次使用成本价
        rt_price = realtime_prices.get(symbol, 0)
        if rt_price <= 0:
            rt_price = realtime_prices.get(strip_prefix(symbol), 0)
        if rt_price <= 0:
            rt_price = avg_cost

        # 计算持仓市值和浮动盈亏
        pos_value = shares * rt_price if shares > 0 and rt_price > 0 else 0
        unrealized = (rt_price - avg_cost) * shares if shares > 0 and avg_cost > 0 else 0

        task_info = {
            "id": t.get("id"),
            "symbol": symbol,
            "task_name": t.get("task_name") or symbol,
            "strategy": t.get("strategy", "grid"),
            "shares": shares,
            "avg_cost": round(avg_cost, 4),
            "current_price": round(rt_price, 4),
            "market_value": round(pos_value, 2),
            "unrealized_pnl": round(unrealized, 2),
            "realized_pnl": round(task_pnl, 2),
            "allocated_funds": round(allocated, 2),
            "task_cash": round(float(t.get("task_cash", 0) or 0), 2),
            "enabled": bool(t.get("enabled", False)),
        }
        task_list.append(task_info)

        market_value += pos_value
        unrealized_pnl += unrealized
        realized_pnl += task_pnl

    result = {
        "task_count": len(task_list),
        "market_value": round(market_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "tasks": task_list,
    }
    logger.info(
        f"[Portfolio] Auto tasks summary for user_id={user_id}: "
        f"tasks={result['task_count']}, mkt_val={result['market_value']}, "
        f"unreal={result['unrealized_pnl']}, realized={result['realized_pnl']}"
    )
    return result


def _query_auto_tasks_sql(user_id):
    """
    直接通过 SQL 查询自动交易任务（兜底方案）
    
    当 ORM 查询失败时，使用原生 SQL 直接查询数据库。
    
    Args:
        user_id: 用户ID
        
    Returns:
        list: 任务字典列表
    """
    from backend.models.db import engine
    from sqlalchemy import text

    sql = "SELECT id, user_id, symbol, strategy, task_name, enabled, position_shares, position_avg_cost, allocated_funds, task_cash, task_pnl, unrealized_pnl FROM auto_trade_tasks WHERE user_id = :uid ORDER BY created_at DESC"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"uid": user_id}).fetchall()

    result = []
    for r in rows:
        keys = r._fields
        d = dict(zip(keys, r))
        result.append(d)
    return result


def place_order(user_id, direction, symbol, name, price, shares, commission, pnl=0, trade_type="manual"):
    """
    下单并记录订单
    
    创建一个新的订单记录并保存到数据库。
    
    Args:
        user_id: 用户ID
        direction: 交易方向，"buy" 或 "sell"
        symbol: 股票代码
        name: 股票名称
        price: 成交价格
        shares: 成交数量
        commission: 手续费
        pnl: 盈亏金额（卖出时有效）
        trade_type: 交易类型，"manual"（手动）、"auto_grid"（网格策略）等
        
    Returns:
        dict: 订单信息字典
    """
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


def execute_trade(user_id, direction, symbol, name, price, shares, trade_type="manual", strategy_type="manual"):
    """
    执行交易（买入或卖出）
    
    根据交易方向执行买入或卖出操作，更新账户资金、持仓和订单记录。
    买入时扣除资金并增加持仓，卖出时减少持仓并增加资金。
    
    持仓按策略类型隔离，同一股票不同策略有独立的持仓记录。
    
    Args:
        user_id: 用户ID
        direction: 交易方向，"buy" 或 "sell"
        symbol: 股票代码
        name: 股票名称
        price: 成交价格
        shares: 成交数量（必须是100的整数倍）
        trade_type: 交易类型，用于标识订单来源
        strategy_type: 策略类型，用于标识持仓来源和隔离
        
    Returns:
        dict: 包含以下字段的交易结果
            - success: 是否成功
            - error: 错误信息（失败时）
            - order: 订单信息（成功时）
            - portfolio: 更新后的账户信息（成功时）
    """
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return {"success": False, "error": "账户不存在，请先重置账户"}

    account = portfolio["account"]
    settings = SimSettings.get(symbol)
    amount = price * shares

    commission = max(amount * settings["commission_rate"], settings["min_commission"])

    if direction == "buy":
        total_cost = amount + commission
        if account["cash"] < total_cost:
            return {"success": False, "error": f"资金不足，需要 {total_cost:.2f}，可用 {account['cash']:.2f}"}

        pos = SimulationPosition.find_by_strategy(user_id, symbol, strategy_type)
        if pos and pos.get("shares", 0) > 0:
            total_cost_shares = pos["shares"] * pos["avg_cost"] + amount
            new_shares = pos["shares"] + shares
            new_avg_cost = total_cost_shares / new_shares
        else:
            new_shares = shares
            new_avg_cost = price

        new_cash = account["cash"] - total_cost
        SimulationAccount.upsert(user_id, account["initial_capital"], new_cash, 0.0, account["realized_pnl"])
        SimulationPosition.upsert(user_id, symbol, name, new_shares, new_avg_cost, price, strategy_type)
        order = place_order(user_id, "buy", symbol, name, price, shares, commission, trade_type=trade_type)
        return {"success": True, "order": order, "portfolio": get_portfolio(user_id)}

    elif direction == "sell":
        pos = SimulationPosition.find_by_strategy(user_id, symbol, strategy_type)
        if not pos or pos.get("shares", 0) < shares:
            available = pos.get("shares", 0) if pos else 0
            return {"success": False, "error": f"策略[{strategy_type}]持仓不足，需要{shares}股，可用{available}股"}

        stamp_tax = amount * settings["stamp_tax_rate"]
        transfer_fee = amount * settings["transfer_fee_rate"] if symbol.startswith("sh") else 0
        total_fees = commission + stamp_tax + transfer_fee
        net_amount = amount - total_fees

        realized_pnl = (price - pos["avg_cost"]) * shares - total_fees
        new_cash = account["cash"] + net_amount
        new_realized_pnl = account["realized_pnl"] + realized_pnl
        SimulationAccount.upsert(user_id, account["initial_capital"], new_cash, 0.0, new_realized_pnl)

        new_shares = pos["shares"] - shares
        SimulationPosition.upsert(user_id, symbol, name, new_shares, pos["avg_cost"], price, strategy_type)

        order = place_order(user_id, "sell", symbol, name, price, shares, total_fees, realized_pnl, trade_type)
        return {"success": True, "order": order, "portfolio": get_portfolio(user_id)}

    return {"success": False, "error": "无效的交易方向"}


def close_all_positions(user_id):
    """
    清仓所有持仓
    
    卖出用户的所有持仓，将资金全部转为现金。
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 包含以下字段的清仓结果
            - success: 是否成功
            - error: 错误信息（失败时）
            - closed: 已清仓的持仓列表
            - portfolio: 更新后的账户信息
    """
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return {"success": False, "error": "账户不存在"}
    closed = []
    for pos in list(portfolio["positions"]):
        result = execute_trade(user_id, "sell", pos["symbol"], pos["name"], pos["current_price"], pos["shares"])
        if result["success"]:
            closed.append(pos)
    return {"success": True, "closed": closed, "portfolio": get_portfolio(user_id)}


def clear_orders(user_id):
    """
    清空订单历史
    
    删除用户的所有订单记录。
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 包含 success 字段的结果
    """
    SimulationOrder.delete_by_user_id(user_id)
    return {"success": True}


def delete_position(user_id, symbol, strategy=None):
    """
    删除指定持仓记录
    
    直接删除持仓数据，不生成订单记录。用于管理操作。
    
    Args:
        user_id: 用户ID
        symbol: 股票代码
        strategy: 策略类型，若为 None 则删除该股票所有策略的持仓
        
    Returns:
        dict: 包含 success 和 portfolio 字段的结果
    """
    from backend.models.simulation import SimPosition
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return {"success": False, "error": "账户不存在"}
    
    try:
        with get_session() as session:
            query = session.query(SimPosition).filter(
                SimPosition.user_id == user_id,
                SimPosition.symbol == symbol
            )
            if strategy:
                query = query.filter(SimPosition.strategy_type == strategy)
            deleted_count = query.delete()
            session.commit()
            
            if deleted_count == 0:
                logger.warning(f"[DeletePosition] user_id={user_id} symbol={symbol} strategy={strategy} 持仓不存在")
                return {"success": False, "error": "持仓不存在"}
            
            logger.info(f"[DeletePosition] user_id={user_id} symbol={symbol} strategy={strategy} 成功删除 {deleted_count} 条持仓记录")
    except Exception as e:
        logger.error(f"[DeletePosition] user_id={user_id} symbol={symbol} strategy={strategy} 删除失败: {e}")
        return {"success": False, "error": f"删除持仓失败: {str(e)}"}
    
    return {"success": True, "portfolio": get_portfolio(user_id)}


def clear_positions(user_id):
    """
    清空所有持仓记录
    
    直接删除所有持仓数据，不生成订单记录。用于管理操作。
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 包含 success 和 portfolio 字段的结果
    """
    from backend.models.simulation import SimPosition
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return {"success": False, "error": "账户不存在"}
    
    with get_session() as session:
        session.query(SimPosition).filter(SimPosition.user_id == user_id).delete()
    
    logger.info(f"[ClearPositions] user_id={user_id}")
    return {"success": True, "portfolio": get_portfolio(user_id)}


def update_prices(user_id, realtime_map):
    """
    更新持仓的当前价格
    
    根据实时行情数据更新所有持仓的当前价格，并重新计算浮动盈亏。
    使用 strip_prefix 和 normalize_symbol 确保符号格式匹配。
    
    Args:
        user_id: 用户ID
        realtime_map: 实时行情数据字典，key 为股票代码，value 为包含 price 字段的字典
        
    Returns:
        dict: 更新后的账户信息，如果账户不存在则返回 None
    """
    from backend.utils.symbol import strip_prefix, normalize_symbol
    portfolio = get_portfolio(user_id)
    if not portfolio:
        return None
    for pos in portfolio["positions"]:
        sym = pos["symbol"]
        rt = realtime_map.get(sym) or realtime_map.get(strip_prefix(sym)) or realtime_map.get(normalize_symbol(sym))
        if rt:
            SimulationPosition.upsert(user_id, pos["symbol"], pos["name"], pos["shares"], pos["avg_cost"], rt["price"], pos.get("strategy_type", "manual"))
    return get_portfolio(user_id)


def update_position_price(user_id, symbol, current_price):
    """
    更新指定股票所有策略持仓的当前价格和浮动盈亏
    
    根据最新价格更新 sim_positions 表中该股票所有策略持仓的 
    current_price、unrealized_pnl、unrealized_pnl_pct。
    供计划任务巡检时调用，确保持仓盈亏数据与实时行情同步。
    
    Args:
        user_id: 用户ID
        symbol: 股票代码
        current_price: 最新价格
        
    Returns:
        int: 更新的持仓记录数量
    """
    positions = SimulationPosition.find_by_user_id(user_id)
    updated_count = 0
    for pos in positions:
        if pos["symbol"] == symbol and pos["shares"] > 0:
            strategy = pos.get("strategy_type", "manual")
            SimulationPosition.upsert(
                user_id, symbol, pos["name"],
                pos["shares"], pos["avg_cost"],
                current_price, strategy
            )
            unrealized = round((current_price - pos["avg_cost"]) * pos["shares"], 2)
            logger.info(
                f"[UpdatePrice] user_id={user_id} symbol={symbol}[{strategy}] "
                f"price={current_price} shares={pos['shares']} avg_cost={pos['avg_cost']} "
                f"unrealized_pnl={unrealized}"
            )
            updated_count += 1
    return updated_count
