"""
Pydantic 模型定义

定义所有 API 的请求和响应数据结构，与前端 TypeScript 类型一一对应。
用于接口数据的校验、序列化和文档生成。
"""

from typing import Optional, List, Dict, Any, Literal, Tuple
from pydantic import BaseModel, Field


# ==================== 认证相关 ====================

class RegisterRequest(BaseModel):
    """用户注册请求模型"""
    username: str = Field(..., min_length=2, max_length=50)                        # 用户名，2-50个字符
    password: str = Field(..., min_length=6)                                       # 密码，最少6个字符


class LoginRequest(BaseModel):
    """用户登录请求模型"""
    username: str                                                                  # 用户名
    password: str                                                                  # 密码


class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: int                                                                        # 用户ID
    username: str                                                                  # 用户名
    created_at: Optional[str] = None                                               # 创建时间


class AuthResponse(BaseModel):
    """认证响应模型（注册/登录通用）"""
    success: bool                                                                  # 操作是否成功
    user: Optional[UserResponse] = None                                            # 用户信息，成功时返回
    error: Optional[str] = None                                                    # 错误信息，失败时返回
    token: Optional[str] = None                                                    # 认证令牌，登录成功时返回


# ==================== 行情数据相关 ====================

class LatestIndicator(BaseModel):
    """最新技术指标数据模型"""
    收盘: float                                                                    # 最新收盘价
    涨跌幅: float                                                                  # 涨跌幅(%)
    MA5: float                                                                     # 5日均线
    MA10: float                                                                    # 10日均线
    MA20: float                                                                    # 20日均线
    MA60: float                                                                    # 60日均线
    RSI: float                                                                     # RSI指标值
    J: float                                                                       # KDJ指标中的J值
    MACD: float                                                                    # MACD值
    MACD_SIGNAL: float                                                             # MACD信号线值
    MACD_HIST: float                                                               # MACD柱状图值
    BB_UPPER: float                                                                # 布林带上轨
    BB_MID: float                                                                  # 布林带中轨
    BB_LOWER: float                                                                # 布林带下轨
    累计净流入: float                                                               # 资金累计净流入
    ATR: float                                                                     # 真实波幅(ATR)


class GridSignal(BaseModel):
    """网格交易信号模型"""
    signal_name: str                                                               # 信号名称
    signal: str                                                                    # 信号类型(买入/卖出/持有/观望)
    signal_text: str                                                               # 信号描述文本
    close: float                                                                   # 当前收盘价
    ma_key: str                                                                    # 均线周期键名(如MA20)
    ma_val: float                                                                  # 均线值
    ma_deviation_pct: float                                                        # 偏离均线百分比
    base_price: float                                                              # 基准价格
    base_label: str                                                                # 基准标签
    atr: Optional[float] = None                                                    # 真实波幅(ATR)
    atr_pct: Optional[float] = None                                                # ATR百分比
    dynamic_spread: bool                                                           # 是否启用动态间距
    grid_count: int                                                                # 网格数量
    grid_spread_pct: float                                                         # 网格间距百分比
    step_pct: float                                                                # 每格步进百分比
    lower_bound: float                                                             # 网格下界价格
    upper_bound: float                                                             # 网格上界价格
    current_grid: int                                                              # 当前所在网格编号
    total_grids: int                                                               # 总网格数
    position_ratio: float                                                          # 仓位比例
    nearby_lower: Optional[float] = None                                           # 附近下网格价格
    nearby_upper: Optional[float] = None                                           # 附近上网格价格
    action_desc: str                                                               # 操作建议描述


class StockDataResponse(BaseModel):
    """股票数据响应模型（K线及技术指标完整数据）"""
    update_time: str                                                               # 数据更新时间
    symbol_name: str                                                               # 股票名称
    symbol: str                                                                    # 股票代码
    start_date: Optional[str] = None                                               # 数据起始日期
    end_date: Optional[str] = None                                                 # 数据结束日期
    dates: List[str]                                                               # 日期序列
    kdata: List[List[float]]                                                       # K线数据序列，每项为 [开盘, 收盘, 最低, 最高]
    volume: List[float]                                                            # 成交量序列
    MA5: List[float]                                                               # 5日均线序列
    MA10: List[float]                                                              # 10日均线序列
    MA20: List[float]                                                              # 20日均线序列
    MA60: List[float]                                                              # 60日均线序列
    MACD: List[float]                                                              # MACD值序列
    MACD_SIGNAL: List[float]                                                       # MACD信号线序列
    MACD_HIST: List[float]                                                         # MACD柱状图序列
    K: List[float]                                                                 # KDJ-K值序列
    D: List[float]                                                                 # KDJ-D值序列
    J: List[float]                                                                 # KDJ-J值序列
    RSI: List[float]                                                               # RSI序列
    BB_UPPER: List[float]                                                          # 布林带上轨序列
    BB_MID: List[float]                                                            # 布林带中轨序列
    BB_LOWER: List[float]                                                          # 布林带下轨序列
    资金净流入: List[float]                                                          # 资金净流入序列
    累计净流入: List[float]                                                          # 累计净流入序列
    latest: LatestIndicator                                                        # 最新技术指标
    signals: List[List[str]]                                                       # 信号列表，每项为 [名称, 状态, 描述]
    grid_signals: Dict[str, GridSignal]                                            # 各均线网格信号字典
    grid_signal: GridSignal                                                        # 当前使用的网格信号
    trade_signal: str                                                              # 综合交易信号(买入/卖出/观望)


# ==================== 实时行情相关 ====================

class RealtimeData(BaseModel):
    """单只股票实时行情数据模型"""
    name: str                                                                      # 股票名称
    price: float                                                                   # 当前价格
    prev_close: float                                                              # 昨日收盘价
    change: float                                                                  # 涨跌额
    change_pct: float                                                              # 涨跌幅(%)
    open: float                                                                    # 开盘价
    high: float                                                                    # 最高价
    low: float                                                                     # 最低价
    volume: float                                                                  # 成交量
    amount: float                                                                  # 成交额
    date: str                                                                      # 日期
    time: str                                                                      # 时间
    source: str                                                                    # 数据来源


class RealtimeResponse(BaseModel):
    """实时行情响应模型"""
    code: int                                                                      # 状态码
    msg: str                                                                       # 状态消息
    update_time: str                                                               # 数据更新时间
    data: Dict[str, RealtimeData]                                                  # 实时行情数据字典，键为股票代码


# ==================== 新闻资讯相关 ====================

class NewsItem(BaseModel):
    """单条新闻资讯模型"""
    title: str                                                                     # 新闻标题
    url: str                                                                       # 新闻链接
    time: str                                                                      # 发布时间
    source: str                                                                    # 新闻来源


class NewsResponse(BaseModel):
    """新闻资讯响应模型"""
    news: List[NewsItem]                                                           # 新闻列表
    update_time: str                                                               # 数据更新时间


# ==================== 信号时间相关 ====================

class SignalTimeRequest(BaseModel):
    """信号时间查询请求模型"""
    symbol: str = "sh518880"                                                       # 股票代码，默认 sh518880
    realtime_price: float                                                          # 实时价格
    prev_close: Optional[float] = None                                             # 昨日收盘价，可选


class SignalTimeResponse(BaseModel):
    """信号时间查询响应模型"""
    code: int                                                                      # 状态码
    msg: str                                                                       # 状态消息
    symbol: str                                                                    # 股票代码
    realtime_price: float                                                          # 实时价格
    prev_close: float                                                              # 昨日收盘价
    change_pct: float                                                              # 涨跌幅(%)
    trade_signal: str                                                              # 综合交易信号
    signals: List[List[str]]                                                       # 信号列表
    grid_signals: Dict[str, GridSignal]                                            # 各均线网格信号字典
    grid_signal: GridSignal                                                        # 当前使用的网格信号
    latest: LatestIndicator                                                        # 最新技术指标


# ==================== 回测相关 ====================

class TradeRecord(BaseModel):
    """回测交易记录模型"""
    entry_date: str                                                                # 买入日期
    entry_price: float                                                             # 买入价格
    entry_grid: int                                                                # 买入时所在网格
    exit_date: str                                                                 # 卖出日期
    exit_price: float                                                              # 卖出价格
    exit_grid: int                                                                 # 卖出时所在网格
    shares: int                                                                    # 交易数量（股）
    pnl: float                                                                     # 盈亏金额
    pnl_pct: float                                                                 # 盈亏百分比(%)


class EquityPoint(BaseModel):
    """回测净值曲线数据点模型"""
    date: str                                                                      # 日期
    equity: float                                                                  # 当日净值


class BacktestParams(BaseModel):
    """回测参数模型"""
    grid_count: int                                                                # 网格数量
    spread_type: str                                                               # 间距类型(fixed固定/dynamic动态)
    base_ma_key: str                                                               # 基础均线周期
    position_size: float                                                           # 仓位大小
    warmup_days: int                                                               # 预热天数


class BacktestRequest(BaseModel):
    """回测请求模型"""
    symbol: str = "sh518880"                                                       # 股票代码，默认 sh518880
    start_date: Optional[str] = None                                               # 回测起始日期，可选
    end_date: Optional[str] = None                                                 # 回测结束日期，可选
    initial_capital: float = 100000.0                                              # 初始资金，默认 10万
    grid_count: int = 10                                                           # 网格数量，默认 10
    spread_type: str = "fixed"                                                     # 间距类型，默认固定间距
    base_ma_key: str = "MA20"                                                      # 基础均线周期，默认 MA20


class BacktestResponse(BaseModel):
    """回测结果响应模型"""
    initial_capital: float                                                         # 初始资金
    final_equity: float                                                            # 最终净值
    total_return: float                                                            # 总收益金额
    total_return_pct: float                                                        # 总收益率(%)
    num_trades: int                                                                # 交易次数
    num_wins: int                                                                  # 盈利次数
    win_rate: float                                                                # 胜率(%)
    max_drawdown_pct: float                                                        # 最大回撤(%)
    equity_curve: List[EquityPoint]                                                # 净值曲线
    trade_history: List[TradeRecord]                                               # 交易历史记录
    params: BacktestParams                                                         # 回测参数


# ==================== 健康检查相关 ====================

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = "ok"                                                             # 服务状态，默认 "ok"

# ==================== 模拟交易相关 ====================

class Position(BaseModel):
    """持仓信息模型"""
    symbol: str                                                                    # 股票代码
    name: str                                                                      # 股票名称
    shares: int                                                                    # 持仓数量（股）
    avg_cost: float                                                                # 平均成本价
    current_price: float                                                           # 当前价格
    unrealized_pnl: float                                                          # 未实现盈亏
    unrealized_pnl_pct: float                                                      # 未实现盈亏百分比(%)
    strategy_type: str = "manual"                                                  # 策略类型，默认手动


class Account(BaseModel):
    """模拟账户信息模型"""
    initial_capital: float                                                         # 初始资金
    cash: float                                                                    # 可用资金
    frozen_cash: float                                                             # 冻结资金
    market_value: float                                                            # 持仓市值
    total_assets: float                                                            # 总资产
    unrealized_pnl: float                                                          # 未实现盈亏
    realized_pnl: float                                                            # 已实现盈亏
    total_pnl: float                                                               # 总盈亏


class SimOrder(BaseModel):
    """模拟订单模型"""
    id: str                                                                        # 订单ID
    direction: str                                                                 # 交易方向(买入/卖出)
    symbol: str                                                                    # 股票代码
    name: str                                                                      # 股票名称
    price: float                                                                   # 成交价格
    shares: int                                                                    # 成交数量（股）
    commission: float                                                              # 手续费
    timestamp: str                                                                 # 成交时间
    pnl: float = 0                                                                 # 盈亏金额，默认 0
    trade_type: str = "manual"                                                     # 交易类型，默认手动


class AutoTaskInfo(BaseModel):
    """自动交易任务摘要信息模型"""
    id: int                                                                        # 任务ID
    symbol: str                                                                    # 股票代码
    task_name: str = ""                                                            # 任务名称
    strategy: str = "grid"                                                         # 策略类型，默认网格
    shares: int = 0                                                                # 持仓数量
    avg_cost: float = 0.0                                                          # 平均成本价
    current_price: float = 0.0                                                     # 当前价格
    market_value: float = 0.0                                                      # 持仓市值
    unrealized_pnl: float = 0.0                                                    # 未实现盈亏
    realized_pnl: float = 0.0                                                      # 已实现盈亏
    allocated_funds: float = 0.0                                                   # 分配资金
    task_cash: float = 0.0                                                         # 任务可用资金
    enabled: bool = False                                                          # 是否启用


class AutoTasksSummary(BaseModel):
    """自动交易任务汇总信息模型"""
    task_count: int = 0                                                            # 任务总数
    market_value: float = 0.0                                                      # 总持仓市值
    unrealized_pnl: float = 0.0                                                    # 总未实现盈亏
    realized_pnl: float = 0.0                                                      # 总已实现盈亏
    tasks: List[AutoTaskInfo] = []                                                 # 任务列表


class SimulationPortfolio(BaseModel):
    """模拟投资组合模型（账户+持仓+订单+自动任务汇总）"""
    account: Account                                                               # 账户信息
    positions: List[Position]                                                      # 持仓列表
    orders: List[SimOrder]                                                         # 订单列表
    auto_tasks: AutoTasksSummary = AutoTasksSummary()                              # 自动交易任务汇总
    total_return: float = 0                                                        # 总收益金额
    total_return_pct: float = 0                                                    # 总收益率(%)


class SimulationOrderRequest(BaseModel):
    """模拟下单请求模型"""
    user_id: int                                                                   # 用户ID
    direction: str                                                                 # 交易方向(买入/卖出)
    symbol: str                                                                    # 股票代码
    name: str                                                                      # 股票名称
    price: float                                                                   # 委托价格
    shares: int                                                                    # 委托数量（股）


class SimulationCloseRequest(BaseModel):
    """模拟清仓请求模型"""
    user_id: int                                                                   # 用户ID


class SimulationResetRequest(BaseModel):
    """模拟账户重置请求模型"""
    user_id: int                                                                   # 用户ID
    initial_capital: float = 100000.0                                              # 重置后的初始资金，默认 10万


class SimulationOrderResponse(BaseModel):
    """模拟下单响应模型"""
    success: bool                                                                  # 下单是否成功
    error: Optional[str] = None                                                    # 错误信息，失败时返回
    order: Optional[SimOrder] = None                                               # 订单信息，成功时返回
    portfolio: Optional[SimulationPortfolio] = None                                # 更新后的投资组合，成功时返回
