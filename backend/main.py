"""
FastAPI 应用主入口

黄金ETF技术分析系统后端 API 服务。
提供K线数据、技术指标、网格交易信号、模拟回测、自动交易等功能。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sys
import os
import logging
from logging.handlers import TimedRotatingFileHandler

# 将项目根目录添加到 Python 模块搜索路径，确保 backend 包可被正确导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 日志配置 ====================

def setup_logging():
    """
    初始化日志系统

    配置两个日志处理器：
        1. 控制台处理器：输出到终端，方便开发调试
        2. 文件处理器：按天分割日志文件，保留最近 7 天，方便问题排查

    日志格式：时间 - 模块名 - 级别 - 消息
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 移除默认处理器，避免重复输出
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 控制台处理器：输出到终端
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件处理器：按天分割日志，保留 7 天
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)  # 确保日志目录存在
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        when='D',            # 按天分割
        backupCount=7,       # 保留 7 天
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

# 应用启动时初始化日志
setup_logging()

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


# ==================== 应用生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用生命周期管理器

    启动时执行：
        1. 初始化数据库表结构
        2. 执行数据库迁移
        3. 检查并启动自动交易调度器

    关闭时执行：
        1. 停止自动交易调度器
    """
    logger = logging.getLogger(__name__)

    # ---------- 启动逻辑 ----------
    # 导入数据库模型，确保表结构被创建
    from backend.models.db import engine, Base
    from backend.models.user import UserModel
    from backend.models.kline import StockKline
    from backend.models.simulation import SimAccount, SimPosition, SimOrder
    from backend.models.settings import SimSetting, SimSymbolSetting
    from backend.models.auto_trade import AutoTradeTaskModel

    # 根据模型定义自动创建所有数据库表
    Base.metadata.create_all(bind=engine)

    # 执行自动交易任务表的数据库迁移
    from backend.models.auto_trade import AutoTradeTask
    AutoTradeTask.migrate_schema()

    # 执行模拟交易订单表的数据库迁移
    from backend.models.simulation import SimulationOrder
    SimulationOrder.migrate_schema()

    # 检查是否有已启用的自动交易任务
    from backend.services.auto_trade_scheduler import AutoTradeScheduler

    enabled_tasks = AutoTradeTask.find_all_enabled()

    logger.info("=" * 50)
    logger.info("黄金ETF技术分析系统 API v2.0 (SQLAlchemy ORM)")
    logger.info("后端启动成功!")
    logger.info("=" * 50)

    # 如果存在已启用的任务，启动调度器
    if enabled_tasks:
        logger.info(f"[Scheduler] 检测到 {len(enabled_tasks)} 个已启用任务，启动调度器")
        await AutoTradeScheduler.start()
    else:
        logger.info("[Scheduler] 无已启用任务，调度器待命（将在首个任务启动时自动激活）")

    yield  # 应用运行中...

    # ---------- 关闭逻辑 ----------
    if AutoTradeScheduler.is_running():
        logger.info("[Scheduler] 正在停止调度器...")
        await AutoTradeScheduler.stop()
    logger.info("系统已关闭")


# ==================== FastAPI 应用实例 ====================

app = FastAPI(
    title="黄金ETF技术分析API",
    description="提供K线数据、技术指标、网格交易信号、模拟回测等功能",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 允许所有来源（生产环境应改为具体域名）
    allow_credentials=True,     # 允许携带认证信息
    allow_methods=["*"],        # 允许所有 HTTP 方法
    allow_headers=["*"],        # 允许所有请求头
)


# ==================== 依赖项 ====================

def get_current_user_dep(authorization: Optional[str] = Header(None)):
    """
    FastAPI 依赖项：从 Authorization 请求头获取当前用户信息

    解析 Bearer Token 格式的 Authorization 头，提取用户身份。

    参数：
        authorization (Optional[str]): HTTP Authorization 请求头值

    返回：
        Optional[Dict]: 用户信息字典，未提供有效 Token 时返回 None
    """
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    # 去除 "Bearer " 前缀，提取 Token
    token = authorization[7:]
    return get_current_user(token)


# ==================== 健康检查接口 ====================

@app.get("/api/health", response_model=HealthResponse, tags=["健康检查"])
async def health_check():
    """
    系统健康检查端点

    请求方式：GET
    请求路径：/api/health

    返回值：{"status": "ok"}
    """
    return HealthResponse(status="ok")


# ==================== 认证接口 ====================

@app.post("/api/auth/register", response_model=AuthResponse, tags=["认证"])
async def register(request: RegisterRequest):
    """
    用户注册接口

    请求方式：POST
    请求路径：/api/auth/register

    请求参数（JSON Body）：
        username (str): 用户名
        password (str): 密码

    返回值（JSON）：
        成功：{"success": True, "user": {"id": ..., "username": ..., "created_at": ...}}
        失败：{"success": False, "error": "用户名已存在"}
    """
    from backend.models.user import User

    # 检查用户名是否已存在
    existing_user = User.find_by_username(request.username)
    if existing_user:
        return AuthResponse(success=False, error="用户名已存在")

    # 创建新用户
    user = User.create(request.username, request.password)
    if not user:
        return AuthResponse(success=False, error="注册失败，请查看后端日志")
    return AuthResponse(
        success=True,
        user={"id": user.id, "username": user.username, "created_at": user.created_at}
    )


@app.post("/api/auth/login", response_model=AuthResponse, tags=["认证"])
async def login(request: LoginRequest):
    """
    用户登录接口

    请求方式：POST
    请求路径：/api/auth/login

    请求参数（JSON Body）：
        username (str): 用户名
        password (str): 密码

    返回值（JSON）：
        成功：{"success": True, "user": {...}, "token": "JWT令牌"}
        失败：{"success": False, "error": "用户名或密码错误"}
    """
    from backend.models.user import User

    # 查找用户并验证密码
    user = User.find_by_username(request.username)
    if not user or not user.verify_password(request.password):
        return AuthResponse(success=False, error="用户名或密码错误")

    # 创建 JWT Token
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return AuthResponse(
        success=True,
        user={"id": user.id, "username": user.username, "created_at": str(user.created_at)},
        token=access_token,
    )


@app.post("/api/auth/logout", tags=["认证"])
async def logout():
    """
    用户登出接口

    请求方式：POST
    请求路径：/api/auth/logout

    返回值：{"success": True}

    注意：JWT 是无状态的，服务端不维护会话，登出只需客户端删除 Token。
    """
    return {"success": True}


@app.get("/api/auth/me", response_model=AuthResponse, tags=["认证"])
async def get_me(authorization: Optional[str] = Header(None)):
    """
    获取当前登录用户信息接口

    请求方式：GET
    请求路径：/api/auth/me

    请求头：
        Authorization: Bearer <token>（可选）

    返回值（JSON）：
        已登录：{"success": True, "user": {"id": ..., "username": ..., "created_at": ...}}
        未登录：{"success": True, "user": None}
    """
    from backend.models.user import User

    # 未提供 Authorization 头
    if not authorization:
        return AuthResponse(success=True, user=None)

    # Authorization 头格式不正确
    if not authorization.startswith("Bearer "):
        return AuthResponse(success=True, user=None)

    # 提取并解码 Token
    token = authorization[7:]
    user_info = get_current_user(token)

    if not user_info:
        return AuthResponse(success=True, user=None)

    # 根据 Token 中的用户 ID 查询最新用户信息
    user = User.find_by_id(user_info["user_id"])
    if not user:
        return AuthResponse(success=True, user=None)

    return AuthResponse(
        success=True,
        user={"id": user.id, "username": user.username, "created_at": user.created_at}
    )


# ==================== 数据接口 ====================

@app.get("/api/data", response_model=StockDataResponse, tags=["数据"])
async def get_data(
    symbol: str = Query(default="sh518880"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    """
    获取K线数据和技术指标接口

    请求方式：GET
    请求路径：/api/data

    查询参数：
        symbol (str, 可选): 股票代码，默认 "sh518880"
        start_date (str, 可选): 开始日期
        end_date (str, 可选): 结束日期

    返回值：包含K线、均线、MACD、KDJ、RSI、布林带等技术指标数据
    """
    from backend.services.gold_data import get_full_data, build_api_response

    try:
        # 获取完整的历史数据
        df = get_full_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        # 构建 API 响应
        response = build_api_response(
            df,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        response["symbol"] = symbol
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 实时行情接口 ====================

@app.get("/api/realtime", response_model=RealtimeResponse, tags=["实时行情"])
async def get_realtime(
    symbol: str = Query(default="518880"),
):
    """
    获取实时行情接口

    请求方式：GET
    请求路径：/api/realtime

    查询参数：
        symbol (str, 可选): 股票代码，默认 "518880"

    返回值：实时行情数据，包含当前价、涨跌幅、成交量等
    """
    from backend.routes import realtime as realtime_module
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"[Realtime API] 请求实时行情: symbol={symbol}")
        result = realtime_module.get_realtime(symbol)
        logger.info(f"[Realtime API] 获取成功: symbols={list(result.get('data', {}).keys())}")
        return result
    except Exception as e:
        logger.error(f"[Realtime API] 获取实时行情失败: symbol={symbol}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 新闻接口 ====================

@app.get("/api/news", response_model=NewsResponse, tags=["新闻"])
async def get_news(symbol: Optional[str] = Query(default=None)):
    """
    获取新闻接口

    请求方式：GET
    请求路径：/api/news

    查询参数：
        symbol (str, 可选): 股票代码

    返回值：新闻列表，包含标题、链接、时间、来源
    """
    from backend.services.news import build_news_response

    try:
        result = build_news_response(symbol)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 实时信号接口 ====================

@app.post("/api/signaltime", response_model=SignalTimeResponse, tags=["实时信号"])
async def post_signaltime(request: SignalTimeRequest):
    """
    根据实时价格计算交易信号接口

    请求方式：POST
    请求路径：/api/signaltime

    请求参数（JSON Body）：
        symbol (str): 股票代码
        realtime_price (float): 实时价格
        prev_close (float, 可选): 昨日收盘价

    返回值：交易信号、网格信号、最新技术指标数据
    """
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


# ==================== 回测接口 ====================

@app.post("/api/backtest", response_model=BacktestResponse, tags=["回测"])
async def post_backtest(request: BacktestRequest):
    """
    运行网格交易回测接口

    请求方式：POST
    请求路径：/api/backtest

    请求参数（JSON Body）：
        symbol (str): 股票代码
        start_date (str, 可选): 开始日期
        end_date (str, 可选): 结束日期
        initial_capital (float): 初始资金，默认 100000.0
        grid_count (int): 网格数量，5/10/15/20
        spread_type (str): 间距类型，"fixed" 或 "atr"
        base_ma_key (str): 基准均线，MA5/MA10/MA20/MA60

    返回值：回测结果，包含收益率、交易记录、权益曲线等
    """
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

        # 获取历史数据
        df = get_full_data(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date
        )

        # 数据不足时无法回测
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


# ==================== 模拟交易接口 ====================

@app.post("/api/simulation", response_model=BacktestResponse, tags=["模拟交易"])
async def post_simulation(request: BacktestRequest):
    """
    运行网格交易模拟接口（与回测共用同一算法）

    请求方式：POST
    请求路径：/api/simulation

    请求参数（JSON Body）：与回测接口相同

    返回值：模拟结果，格式与回测接口相同
    """
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

        # 获取历史数据
        df = get_full_data(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date
        )

        # 数据不足时无法模拟
        if len(df) < 30:
            raise HTTPException(status_code=400, detail="数据不足，无法模拟")

        # 执行模拟（复用回测算法）
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


# ==================== 模拟交易管理接口 ====================

from backend.models.schemas import (
    SimulationOrderRequest,
    SimulationResetRequest,
    SimulationCloseRequest,
    SimulationPortfolio,
    SimulationOrderResponse,
    Position,
    Account,
    SimOrder,
    AutoTasksSummary,
    AutoTaskInfo,
)
from backend.services import simulation_trade as st


def _build_portfolio(portfolio_dict):
    """
    将模拟交易组合字典构建为 Pydantic 模型对象

    参数：
        portfolio_dict (dict): 模拟交易组合原始字典数据

    返回：
        SimulationPortfolio: 包含账户、持仓、订单、自动任务等信息的 Pydantic 模型
    """
    # 提取自动任务信息，若无则为空字典
    at = portfolio_dict.get("auto_tasks") or {}
    return SimulationPortfolio(
        account=Account(**portfolio_dict["account"]),              # 账户信息
        positions=[Position(**p) for p in portfolio_dict["positions"]],  # 持仓列表
        orders=[SimOrder(**o) for o in portfolio_dict["orders"][:20]],   # 最近20条订单
        auto_tasks=AutoTasksSummary(
            task_count=at.get("task_count", 0),                    # 任务数量
            market_value=at.get("market_value", 0.0),             # 持仓市值
            unrealized_pnl=at.get("unrealized_pnl", 0.0),         # 未实现盈亏
            realized_pnl=at.get("realized_pnl", 0.0),             # 已实现盈亏
            tasks=[AutoTaskInfo(**t) for t in at.get("tasks", [])],  # 任务列表
        ),
        total_return=portfolio_dict.get("total_return", 0),       # 总收益
        total_return_pct=portfolio_dict.get("total_return_pct", 0),  # 总收益率
    )


@app.post("/api/simulation/reset", response_model=SimulationPortfolio, tags=["模拟交易"])
async def reset_simulation(request: SimulationResetRequest):
    """
    重置模拟账户接口

    请求方式：POST
    请求路径：/api/simulation/reset

    请求参数（JSON Body）：
        user_id (int): 用户 ID
        initial_capital (float): 初始资金

    返回值：重置后的模拟账户组合信息
    """
    try:
        portfolio = st.reset_portfolio(request.user_id, request.initial_capital)
        return _build_portfolio(portfolio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/order", response_model=SimulationOrderResponse, tags=["模拟交易"])
async def place_order(request: SimulationOrderRequest):
    """
    模拟交易下单接口（买入或卖出）

    请求方式：POST
    请求路径：/api/simulation/order

    请求参数（JSON Body）：
        user_id (int): 用户 ID
        direction (str): 交易方向，"buy" 或 "sell"
        symbol (str): 股票代码
        name (str): 股票名称
        price (float): 交易价格
        shares (int): 交易数量（股）

    返回值：订单信息和更新后的组合信息
    """
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
            portfolio=_build_portfolio(portfolio)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/portfolio", response_model=SimulationPortfolio, tags=["模拟交易"])
async def get_portfolio(authorization: Optional[str] = Header(None)):
    """
    获取当前模拟账户持仓接口

    请求方式：GET
    请求路径：/api/simulation/portfolio

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：模拟账户组合信息，包含账户、持仓、订单等
    """
    try:
        # 从 Authorization 头提取用户信息
        user_info = None
        if authorization and authorization.startswith("Bearer "):
            user_info = get_current_user(authorization[7:])
        if not user_info:
            raise HTTPException(status_code=401, detail="未登录")

        # 获取用户模拟账户组合
        portfolio = st.get_portfolio(user_info["user_id"])
        if not portfolio:
            raise HTTPException(status_code=404, detail="账户不存在")

        return _build_portfolio(portfolio)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/close", response_model=SimulationOrderResponse, tags=["模拟交易"])
async def close_positions(request: SimulationCloseRequest):
    """
    清仓接口（卖出所有持仓）

    请求方式：POST
    请求路径：/api/simulation/close

    请求参数（JSON Body）：
        user_id (int): 用户 ID

    返回值：清仓后的组合信息
    """
    try:
        result = st.close_all_positions(request.user_id)
        if not result["success"]:
            return SimulationOrderResponse(success=False, error=result["error"])

        portfolio = result["portfolio"]
        return SimulationOrderResponse(
            success=True,
            portfolio=_build_portfolio(portfolio)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/orders/clear", tags=["模拟交易"])
async def clear_orders(authorization: Optional[str] = Header(None)):
    """
    清空成交记录接口

    请求方式：POST
    请求路径：/api/simulation/orders/clear

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：{"success": True}
    """
    try:
        # 从 Authorization 头提取用户信息
        user_info = None
        if authorization and authorization.startswith("Bearer "):
            user_info = get_current_user(authorization[7:])
        if not user_info:
            raise HTTPException(status_code=401, detail="未登录")
        # 清空该用户的成交记录
        st.clear_orders(user_info["user_id"])
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 系统设置接口 ====================

from backend.models.settings import SimSettings

@app.get("/api/settings", tags=["系统设置"])
async def get_settings():
    """
    获取默认手续费设置接口

    请求方式：GET
    请求路径：/api/settings

    返回值：默认手续费配置，包含佣金率、最低佣金、印花税率、过户费率
    """
    return SimSettings.get()


@app.put("/api/settings", tags=["系统设置"])
async def update_settings(request: dict):
    """
    更新默认手续费设置接口

    请求方式：PUT
    请求路径：/api/settings

    请求参数（JSON Body）：
        commission_rate (float, 可选): 佣金费率，默认 0.0003
        min_commission (float, 可选): 最低佣金（元），默认 5.0
        stamp_tax_rate (float, 可选): 印花税费率，默认 0.001
        transfer_fee_rate (float, 可选): 过户费率，默认 0.00002

    返回值：更新后的手续费配置
    """
    settings = SimSettings.update(
        commission_rate=float(request.get("commission_rate", 0.0003)),
        min_commission=float(request.get("min_commission", 5.0)),
        stamp_tax_rate=float(request.get("stamp_tax_rate", 0.001)),
        transfer_fee_rate=float(request.get("transfer_fee_rate", 0.00002)),
    )
    return settings


@app.get("/api/settings/symbols", tags=["系统设置"])
async def get_all_symbol_settings():
    """
    获取所有单票手续费设置接口

    请求方式：GET
    请求路径：/api/settings/symbols

    返回值：所有已配置单票手续费的列表
    """
    return SimSettings.get_all_symbol_settings()


@app.get("/api/settings/symbol/{symbol}", tags=["系统设置"])
async def get_symbol_settings(symbol: str):
    """
    获取指定证券的手续费设置接口（包含默认值回退）

    请求方式：GET
    请求路径：/api/settings/symbol/{symbol}

    路径参数：
        symbol (str): 股票代码

    返回值：该证券的手续费配置（若未单独配置则使用默认值）
    """
    return {"symbol": symbol, **SimSettings.get(symbol)}


@app.put("/api/settings/symbol/{symbol}", tags=["系统设置"])
async def upsert_symbol_settings(symbol: str, request: dict):
    """
    设置单票手续费接口（None 表示使用默认值）

    请求方式：PUT
    请求路径：/api/settings/symbol/{symbol}

    路径参数：
        symbol (str): 股票代码

    请求参数（JSON Body）：
        commission_rate (float|None): 佣金费率，None 表示使用默认值
        min_commission (float|None): 最低佣金，None 表示使用默认值
        stamp_tax_rate (float|None): 印花税费率，None 表示使用默认值
        transfer_fee_rate (float|None): 过户费率，None 表示使用默认值

    返回值：更新后的单票手续费配置
    """
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
    """
    删除单票手续费设置接口（恢复使用默认值）

    请求方式：DELETE
    请求路径：/api/settings/symbol/{symbol}

    路径参数：
        symbol (str): 股票代码

    返回值：删除后的手续费配置（回退到默认值）
    """
    SimSettings.delete_symbol_settings(symbol)
    return {"symbol": symbol, **SimSettings.get()}


# ==================== 自动交易接口（多任务管理） ====================

from backend.services.auto_trade import AutoTradeService

def _get_user(authorization: Optional[str]):
    """
    从 Authorization 头提取用户信息的辅助函数

    参数：
        authorization (Optional[str]): HTTP Authorization 请求头值

    返回：
        Optional[Dict]: 用户信息字典，无效时返回 None
    """
    if authorization and authorization.startswith("Bearer "):
        return get_current_user(authorization[7:])
    return None


@app.get("/api/autotrade/tasks", tags=["自动交易"])
async def get_autotrade_tasks(authorization: Optional[str] = Header(None)):
    """
    获取用户所有自动交易任务接口

    请求方式：GET
    请求路径：/api/autotrade/tasks

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：用户所有自动交易任务的状态列表
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return AutoTradeService.get_all_status(user_info["user_id"])


@app.post("/api/autotrade/tasks", tags=["自动交易"])
async def create_autotrade_task(request: dict, authorization: Optional[str] = Header(None)):
    """
    新增自动交易任务接口

    请求方式：POST
    请求路径：/api/autotrade/tasks

    请求头：
        Authorization: Bearer <token>（必须）

    请求参数（JSON Body）：
        symbol (str): 股票代码（必填）
        其他策略参数...

    返回值：创建的任务信息
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    # 提取并验证股票代码
    symbol = request.get("symbol", "").strip().lower()
    if not symbol:
        raise HTTPException(status_code=400, detail="证券代码不能为空")
    result = await AutoTradeService.add_task(user_info["user_id"], symbol, request)
    return result


@app.delete("/api/autotrade/tasks/{task_id}", tags=["自动交易"])
async def delete_autotrade_task(task_id: int, authorization: Optional[str] = Header(None)):
    """
    删除自动交易任务接口

    请求方式：DELETE
    请求路径：/api/autotrade/tasks/{task_id}

    路径参数：
        task_id (int): 任务 ID

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：删除结果
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = await AutoTradeService.delete_task(task_id)
    return result


@app.put("/api/autotrade/tasks/{task_id}", tags=["自动交易"])
async def update_autotrade_task(task_id: int, request: dict, authorization: Optional[str] = Header(None)):
    """
    更新自动交易任务配置接口

    请求方式：PUT
    请求路径：/api/autotrade/tasks/{task_id}

    路径参数：
        task_id (int): 任务 ID

    请求头：
        Authorization: Bearer <token>（必须）

    请求参数（JSON Body）：需要更新的任务配置字段

    返回值：更新后的任务信息
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = AutoTradeService.update_task_config(task_id, request)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "任务不存在"))
    return result


@app.post("/api/autotrade/tasks/{task_id}/start", tags=["自动交易"])
async def start_autotrade_task(task_id: int, authorization: Optional[str] = Header(None)):
    """
    启动单个自动交易任务接口

    请求方式：POST
    请求路径：/api/autotrade/tasks/{task_id}/start

    路径参数：
        task_id (int): 任务 ID

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：启动结果
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = await AutoTradeService.start_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "启动失败"))
    return result


@app.post("/api/autotrade/tasks/{task_id}/stop", tags=["自动交易"])
async def stop_autotrade_task(task_id: int, authorization: Optional[str] = Header(None)):
    """
    停止单个自动交易任务接口

    请求方式：POST
    请求路径：/api/autotrade/tasks/{task_id}/stop

    路径参数：
        task_id (int): 任务 ID

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：停止结果
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    result = await AutoTradeService.stop_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "停止失败"))
    return result


@app.get("/api/autotrade/strategies", tags=["自动交易"])
async def list_autotrade_strategies():
    """
    获取所有可用的交易策略接口

    请求方式：GET
    请求路径：/api/autotrade/strategies

    返回值：可用策略列表及其参数说明
    """
    from backend.services.strategies import StrategyFactory
    return StrategyFactory.list_all()


@app.post("/api/autotrade/tasks/start-all", tags=["自动交易"])
async def start_all_autotrade_tasks(authorization: Optional[str] = Header(None)):
    """
    启动所有自动交易任务接口

    请求方式：POST
    请求路径：/api/autotrade/tasks/start-all

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：批量启动结果
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return await AutoTradeService.start_all_tasks(user_info["user_id"])


@app.post("/api/autotrade/tasks/stop-all", tags=["自动交易"])
async def stop_all_autotrade_tasks(authorization: Optional[str] = Header(None)):
    """
    停止所有自动交易任务接口

    请求方式：POST
    请求路径：/api/autotrade/tasks/stop-all

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：批量停止结果
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return await AutoTradeService.stop_all_tasks(user_info["user_id"])


@app.get("/api/autotrade/summary", tags=["自动交易"])
async def get_autotrade_summary(authorization: Optional[str] = Header(None)):
    """
    获取自动交易任务汇总数据接口（用于与共享账户对账）

    请求方式：GET
    请求路径：/api/autotrade/summary

    请求头：
        Authorization: Bearer <token>（必须）

    返回值：自动交易任务的汇总数据，包含各任务的盈亏统计
    """
    user_info = _get_user(authorization)
    if not user_info:
        raise HTTPException(status_code=401, detail="未登录")
    return AutoTradeScheduler.get_task_summary(user_info["user_id"])


# ==================== 应用启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    # 以 0.0.0.0 监听所有网络接口，端口 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
