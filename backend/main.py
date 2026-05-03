"""
FastAPI 应用入口

黄金ETF技术分析系统后端 API
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.schemas import (
    HealthResponse,
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    StockDataResponse,
    RealtimeResponse,
    NewsResponse,
    BacktestRequest,
    BacktestResponse,
    SignalTimeRequest,
    SignalTimeResponse,
)
from backend.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

# ==================== FastAPI App ====================

app = FastAPI(
    title="黄金ETF技术分析API",
    description="提供K线数据、技术指标、网格交易信号、模拟回测等功能",
    version="2.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 依赖项 ====================

def get_current_user_dep(authorization: Optional[str] = Header(None)):
    """从 Authorization header 获取当前用户"""
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    return get_current_user(token)


# ==================== Health ====================

@app.get("/api/health", response_model=HealthResponse, tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    return HealthResponse(status="ok")


# ==================== Auth ====================

@app.post("/api/auth/register", response_model=AuthResponse, tags=["认证"])
async def register(request: RegisterRequest):
    """用户注册"""
    from backend.models.user import User

    # 检查是否已存在
    existing_user = User.find_by_username(request.username)
    if existing_user:
        return AuthResponse(success=False, error="用户名已存在")

    # 创建用户
    user = User.create(request.username, request.password)
    return AuthResponse(
        success=True,
        user={"id": user.id, "username": user.username, "created_at": user.created_at}
    )


@app.post("/api/auth/login", response_model=AuthResponse, tags=["认证"])
async def login(request: LoginRequest):
    """用户登录，返回 JWT token"""
    from backend.models.user import User

    user = User.find_by_username(request.username)
    if not user or not user.verify_password(request.password):
        return AuthResponse(success=False, error="用户名或密码错误")

    # 创建 JWT token
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return AuthResponse(
        success=True,
        user={"id": user.id, "username": user.username, "created_at": user.created_at},
        token=access_token,
    )


@app.post("/api/auth/logout", tags=["认证"])
async def logout():
    """用户登出（JWT 无状态，只需客户端删除 token）"""
    return {"success": True}


@app.get("/api/auth/me", response_model=AuthResponse, tags=["认证"])
async def get_me(authorization: Optional[str] = Header(None)):
    """获取当前登录用户信息"""
    from backend.models.user import User

    if not authorization:
        return AuthResponse(success=True, user=None)

    if not authorization.startswith("Bearer "):
        return AuthResponse(success=True, user=None)

    token = authorization[7:]
    user_info = get_current_user(token)

    if not user_info:
        return AuthResponse(success=True, user=None)

    user = User.find_by_id(user_info["user_id"])
    if not user:
        return AuthResponse(success=True, user=None)

    return AuthResponse(
        success=True,
        user={"id": user.id, "username": user.username, "created_at": user.created_at}
    )


# ==================== Data ====================

@app.get("/api/data", response_model=StockDataResponse, tags=["数据"])
async def get_data(
    symbol: str = Query(default="sh518880"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    """获取K线数据和技术指标"""
    from backend.services.gold_data import get_full_data, build_api_response

    try:
        df = get_full_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        response = build_api_response(
            df,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        response["symbol"] = symbol
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Realtime ====================

@app.get("/api/realtime", response_model=RealtimeResponse, tags=["实时行情"])
async def get_realtime(
    symbol: str = Query(default="sh518880"),
):
    """获取实时行情"""
    from backend.routes import realtime as realtime_module

    try:
        result = realtime_module.get_realtime(symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== News ====================

@app.get("/api/news", response_model=NewsResponse, tags=["新闻"])
async def get_news(symbol: Optional[str] = Query(default=None)):
    """获取新闻"""
    from backend.services.news import build_news_response

    try:
        result = build_news_response(symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SignalTime ====================

@app.post("/api/signaltime", response_model=SignalTimeResponse, tags=["实时信号"])
async def post_signaltime(request: SignalTimeRequest):
    """根据实时价格计算交易信号"""
    from backend.routes import signaltime as signaltime_module

    try:
        result = signaltime_module.calc_signaltime(
            symbol=request.symbol,
            realtime_price=request.realtime_price,
            prev_close=request.prev_close
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Backtest ====================

@app.post("/api/backtest", response_model=BacktestResponse, tags=["回测"])
async def post_backtest(request: BacktestRequest):
    """运行网格交易回测"""
    from backend.services.backtest import run_grid_backtest
    from backend.services.gold_data import get_full_data

    try:
        # 参数验证
        if request.grid_count not in [5, 10, 15, 20]:
            raise HTTPException(status_code=400, detail="grid_count 必须是 5/10/15/20 之一")
        if request.spread_type not in ["fixed", "atr"]:
            raise HTTPException(status_code=400, detail="spread_type 必须是 fixed 或 atr")
        if request.base_ma_key not in ["MA5", "MA10", "MA20", "MA60"]:
            raise HTTPException(status_code=400, detail="base_ma_key 无效")

        # 获取数据
        df = get_full_data(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if len(df) < 30:
            raise HTTPException(status_code=400, detail="数据不足，无法回测")

        # 执行回测
        result = run_grid_backtest(
            df=df,
            initial_capital=request.initial_capital,
            grid_count=request.grid_count,
            spread_type=request.spread_type,
            base_ma_key=request.base_ma_key
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测执行失败: {str(e)}")


# ==================== 模拟交易 ====================

@app.post("/api/simulation", response_model=BacktestResponse, tags=["模拟交易"])
async def post_simulation(request: BacktestRequest):
    """运行网格交易模拟（与回测共用同一算法）"""
    from backend.services.backtest import run_grid_backtest
    from backend.services.gold_data import get_full_data

    try:
        if request.grid_count not in [5, 10, 15, 20]:
            raise HTTPException(status_code=400, detail="grid_count 必须是 5/10/15/20 之一")
        if request.spread_type not in ["fixed", "atr"]:
            raise HTTPException(status_code=400, detail="spread_type 必须是 fixed 或 atr")
        if request.base_ma_key not in ["MA5", "MA10", "MA20", "MA60"]:
            raise HTTPException(status_code=400, detail="base_ma_key 无效")

        df = get_full_data(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date
        )

        if len(df) < 30:
            raise HTTPException(status_code=400, detail="数据不足，无法模拟")

        result = run_grid_backtest(
            df=df,
            initial_capital=request.initial_capital,
            grid_count=request.grid_count,
            spread_type=request.spread_type,
            base_ma_key=request.base_ma_key
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模拟执行失败: {str(e)}")


# ==================== 启动信息 ====================

@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("黄金ETF技术分析系统 API v2.0")
    print("FastAPI backend started")
    print("=" * 50)


# ==================== Simulation Trading APIs ====================

from backend.models.schemas import (
    SimulationOrderRequest,
    SimulationResetRequest,
    SimulationCloseRequest,
    SimulationPortfolio,
    SimulationOrderResponse,
    Position,
    Account,
    SimOrder,
)
from backend.services import simulation_trade as st

@app.post("/api/simulation/reset", response_model=SimulationPortfolio, tags=["模拟交易"])
async def reset_simulation(request: SimulationResetRequest):
    """重置模拟账户"""
    try:
        portfolio = st.reset_portfolio(request.user_id, request.initial_capital)
        return SimulationPortfolio(
            account=Account(**portfolio["account"]),
            positions=[Position(**p) for p in portfolio["positions"]],
            orders=[SimOrder(**o) for o in portfolio["orders"]]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/order", response_model=SimulationOrderResponse, tags=["模拟交易"])
async def place_order(request: SimulationOrderRequest):
    """下单买入或卖出"""
    try:
        result = st.execute_trade(
            request.user_id,
            request.direction,
            request.symbol,
            request.name,
            request.price,
            request.shares
        )
        if not result["success"]:
            return SimulationOrderResponse(success=False, error=result["error"])
        
        order = result["order"]
        portfolio = result["portfolio"]
        return SimulationOrderResponse(
            success=True,
            order=SimOrder(**order),
            portfolio=SimulationPortfolio(
                account=Account(**portfolio["account"]),
                positions=[Position(**p) for p in portfolio["positions"]],
                orders=[SimOrder(**o) for o in portfolio["orders"][:20]]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/simulation/portfolio", response_model=SimulationPortfolio, tags=["模拟交易"])
async def get_portfolio(authorization: Optional[str] = Header(None)):
    """获取当前账户持仓"""
    try:
        user_info = None
        if authorization and authorization.startswith("Bearer "):
            user_info = get_current_user(authorization[7:])
        if not user_info:
            raise HTTPException(status_code=401, detail="未登录")
        
        portfolio = st.get_portfolio(user_info["user_id"])
        if not portfolio:
            raise HTTPException(status_code=404, detail="账户不存在")
        
        return SimulationPortfolio(
            account=Account(**portfolio["account"]),
            positions=[Position(**p) for p in portfolio["positions"]],
            orders=[SimOrder(**o) for o in portfolio["orders"][:20]]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/close", response_model=SimulationOrderResponse, tags=["模拟交易"])
async def close_positions(request: SimulationCloseRequest):
    """清仓"""
    try:
        result = st.close_all_positions(request.user_id)
        if not result["success"]:
            return SimulationOrderResponse(success=False, error=result["error"])

        portfolio = result["portfolio"]
        return SimulationOrderResponse(
            success=True,
            portfolio=SimulationPortfolio(
                account=Account(**portfolio["account"]),
                positions=[Position(**p) for p in portfolio["positions"]],
                orders=[SimOrder(**o) for o in portfolio["orders"][:20]]
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulation/orders/clear", tags=["模拟交易"])
async def clear_orders(authorization: Optional[str] = Header(None)):
    """清空成交记录"""
    try:
        user_info = None
        if authorization and authorization.startswith("Bearer "):
            user_info = get_current_user(authorization[7:])
        if not user_info:
            raise HTTPException(status_code=401, detail="未登录")
        st.clear_orders(user_info["user_id"])
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Settings APIs ====================

from backend.models.settings import SimSettings

@app.get("/api/settings", tags=["系统设置"])
async def get_settings():
    """获取默认手续费设置"""
    return SimSettings.get()

@app.put("/api/settings", tags=["系统设置"])
async def update_settings(request: dict):
    """更新默认手续费设置"""
    settings = SimSettings.update(
        commission_rate=float(request.get("commission_rate", 0.0003)),
        min_commission=float(request.get("min_commission", 5.0)),
        stamp_tax_rate=float(request.get("stamp_tax_rate", 0.001)),
        transfer_fee_rate=float(request.get("transfer_fee_rate", 0.00002)),
    )
    return settings

@app.get("/api/settings/symbols", tags=["系统设置"])
async def get_all_symbol_settings():
    """获取所有单票手续费设置"""
    return SimSettings.get_all_symbol_settings()

@app.get("/api/settings/symbol/{symbol}", tags=["系统设置"])
async def get_symbol_settings(symbol: str):
    """获取指定证券的手续费设置（包含默认值）"""
    return {"symbol": symbol, **SimSettings.get(symbol)}

@app.put("/api/settings/symbol/{symbol}", tags=["系统设置"])
async def upsert_symbol_settings(symbol: str, request: dict):
    """设置单票手续费（None表示使用默认）"""
    result = SimSettings.upsert_symbol_settings(
        symbol,
        commission_rate=float(request["commission_rate"]) if request.get("commission_rate") is not None else None,
        min_commission=float(request["min_commission"]) if request.get("min_commission") is not None else None,
        stamp_tax_rate=float(request["stamp_tax_rate"]) if request.get("stamp_tax_rate") is not None else None,
        transfer_fee_rate=float(request["transfer_fee_rate"]) if request.get("transfer_fee_rate") is not None else None,
    )
    return {"symbol": symbol, **result}

@app.delete("/api/settings/symbol/{symbol}", tags=["系统设置"])
async def delete_symbol_settings(symbol: str):
    """删除单票手续费设置，恢复默认"""
    SimSettings.delete_symbol_settings(symbol)
    return {"symbol": symbol, **SimSettings.get()}


# ==================== Auto Trade APIs (multi-task) ====================

from backend.services.auto_trade import AutoTradeService

def _get_user(authorization: Optional[str]):
    if authorization and authorization.startswith("Bearer "):
        return get_current_user(authorization[7:])
    return None

@app.get("/api/autotrade/tasks", tags=["自动交易"])
async def get_autotrade_tasks(authorization: Optional[str] = Header(None)):
    """获取用户所有自动交易任务"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return AutoTradeService.get_all_status(user_info["user_id"])

@app.post("/api/autotrade/tasks", tags=["自动交易"])
async def create_autotrade_task(request: dict, authorization: Optional[str] = Header(None)):
    """新增自动交易任务"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    symbol = request.get("symbol", "").strip().lower()
    if not symbol:
        raise HTTPException(status_code=400, detail="证券代码不能为空")
    result = await AutoTradeService.add_task(user_info["user_id"], symbol, request)
    return result

@app.delete("/api/autotrade/tasks/{symbol}", tags=["自动交易"])
async def delete_autotrade_task(symbol: str, authorization: Optional[str] = Header(None)):
    """删除自动交易任务"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = await AutoTradeService.delete_task(user_info["user_id"], symbol.lower())
    return result

@app.put("/api/autotrade/tasks/{symbol}", tags=["自动交易"])
async def update_autotrade_task(symbol: str, request: dict, authorization: Optional[str] = Header(None)):
    """更新自动交易任务配置"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = AutoTradeService.update_task_config(user_info["user_id"], symbol.lower(), request)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "任务不存在"))
    return result

@app.post("/api/autotrade/tasks/{symbol}/start", tags=["自动交易"])
async def start_autotrade_task(symbol: str, authorization: Optional[str] = Header(None)):
    """启动单个自动交易任务"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = await AutoTradeService.start_task(user_info["user_id"], symbol.lower())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "启动失败"))
    return result

@app.post("/api/autotrade/tasks/{symbol}/stop", tags=["自动交易"])
async def stop_autotrade_task(symbol: str, authorization: Optional[str] = Header(None)):
    """停止单个自动交易任务"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = await AutoTradeService.stop_task(user_info["user_id"], symbol.lower())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "停止失败"))
    return result

@app.post("/api/autotrade/tasks/start-all", tags=["自动交易"])
async def start_all_autotrade_tasks(authorization: Optional[str] = Header(None)):
    """启动所有自动交易任务"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return await AutoTradeService.start_all_tasks(user_info["user_id"])

@app.post("/api/autotrade/tasks/stop-all", tags=["自动交易"])
async def stop_all_autotrade_tasks(authorization: Optional[str] = Header(None)):
    """停止所有自动交易任务"""
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return await AutoTradeService.stop_all_tasks(user_info["user_id"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
