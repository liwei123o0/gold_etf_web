"""
Pydantic 模型定义

定义所有 API 的请求和响应数据结构，与前端 TypeScript 类型一一对应。
"""

from typing import Optional, List, Dict, Any, Literal, Tuple
from pydantic import BaseModel, Field


# ==================== Auth ====================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    user: Optional[UserResponse] = None
    error: Optional[str] = None
    token: Optional[str] = None


# ==================== Data ====================

class LatestIndicator(BaseModel):
    收盘: float
    涨跌幅: float
    MA5: float
    MA10: float
    MA20: float
    MA60: float
    RSI: float
    J: float
    MACD: float
    MACD_SIGNAL: float
    MACD_HIST: float
    BB_UPPER: float
    BB_MID: float
    BB_LOWER: float
    累计净流入: float
    ATR: float


class GridSignal(BaseModel):
    signal_name: str
    signal: str  # 买入/卖出/持有/观望
    signal_text: str
    close: float
    ma_key: str
    ma_val: float
    ma_deviation_pct: float
    base_price: float
    base_label: str
    atr: Optional[float] = None
    atr_pct: Optional[float] = None
    dynamic_spread: bool
    grid_count: int
    grid_spread_pct: float
    step_pct: float
    lower_bound: float
    upper_bound: float
    current_grid: int
    total_grids: int
    position_ratio: float
    nearby_lower: Optional[float] = None
    nearby_upper: Optional[float] = None
    action_desc: str


class StockDataResponse(BaseModel):
    update_time: str
    symbol_name: str
    symbol: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    dates: List[str]
    kdata: List[List[float]]  # [开盘, 收盘, 最低, 最高]
    volume: List[float]
    MA5: List[float]
    MA10: List[float]
    MA20: List[float]
    MA60: List[float]
    MACD: List[float]
    MACD_SIGNAL: List[float]
    MACD_HIST: List[float]
    K: List[float]
    D: List[float]
    J: List[float]
    RSI: List[float]
    BB_UPPER: List[float]
    BB_MID: List[float]
    BB_LOWER: List[float]
    资金净流入: List[float]
    累计净流入: List[float]
    latest: LatestIndicator
    signals: List[List[str]]  # [[名称, 状态, 描述], ...]
    grid_signals: Dict[str, GridSignal]
    grid_signal: GridSignal
    trade_signal: str  # 买入/卖出/观望


# ==================== Realtime ====================

class RealtimeData(BaseModel):
    name: str
    price: float
    prev_close: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    volume: float
    amount: float
    date: str
    time: str
    source: str


class RealtimeResponse(BaseModel):
    code: int
    msg: str
    update_time: str
    data: Dict[str, RealtimeData]


# ==================== News ====================

class NewsItem(BaseModel):
    title: str
    url: str
    time: str
    source: str


class NewsResponse(BaseModel):
    news: List[NewsItem]
    update_time: str


# ==================== SignalTime ====================

class SignalTimeRequest(BaseModel):
    symbol: str = "sh518880"
    realtime_price: float
    prev_close: Optional[float] = None


class SignalTimeResponse(BaseModel):
    code: int
    msg: str
    symbol: str
    realtime_price: float
    prev_close: float
    change_pct: float
    trade_signal: str
    signals: List[List[str]]
    grid_signals: Dict[str, GridSignal]
    grid_signal: GridSignal
    latest: LatestIndicator


# ==================== Backtest ====================

class TradeRecord(BaseModel):
    entry_date: str
    entry_price: float
    entry_grid: int
    exit_date: str
    exit_price: float
    exit_grid: int
    shares: int
    pnl: float
    pnl_pct: float


class EquityPoint(BaseModel):
    date: str
    equity: float


class BacktestParams(BaseModel):
    grid_count: int
    spread_type: str
    base_ma_key: str
    position_size: float
    warmup_days: int


class BacktestRequest(BaseModel):
    symbol: str = "sh518880"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 100000.0
    grid_count: int = 10
    spread_type: str = "fixed"
    base_ma_key: str = "MA20"


class BacktestResponse(BaseModel):
    initial_capital: float
    final_equity: float
    total_return: float
    total_return_pct: float
    num_trades: int
    num_wins: int
    win_rate: float
    max_drawdown_pct: float
    equity_curve: List[EquityPoint]
    trade_history: List[TradeRecord]
    params: BacktestParams


# ==================== Health ====================

class HealthResponse(BaseModel):
    status: str = "ok"

# ==================== Simulation Trading ====================

class Position(BaseModel):
    symbol: str
    name: str
    shares: int
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class Account(BaseModel):
    initial_capital: float
    cash: float
    frozen_cash: float
    market_value: float
    total_assets: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float


class SimOrder(BaseModel):
    id: str
    direction: str
    symbol: str
    name: str
    price: float
    shares: int
    commission: float
    timestamp: str
    pnl: float = 0


class SimulationPortfolio(BaseModel):
    account: Account
    positions: List[Position]
    orders: List[SimOrder]
    total_return: float = 0
    total_return_pct: float = 0


class SimulationOrderRequest(BaseModel):
    user_id: int
    direction: str
    symbol: str
    name: str
    price: float
    shares: int


class SimulationCloseRequest(BaseModel):
    user_id: int


class SimulationResetRequest(BaseModel):
    user_id: int
    initial_capital: float = 100000.0


class SimulationOrderResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    order: Optional[SimOrder] = None
    portfolio: Optional[SimulationPortfolio] = None
