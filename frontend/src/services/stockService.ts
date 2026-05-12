import api from './api'

export interface LatestIndicator {
  收盘: number
  涨跌幅: number
  MA5: number
  MA10: number
  MA20: number
  MA60: number
  RSI: number
  J: number
  MACD: number
  MACD_SIGNAL: number
  MACD_HIST: number
  BB_UPPER: number
  BB_MID: number
  BB_LOWER: number
  累计净流入: number
  ATR: number
}

export interface GridSignal {
  signal_name: string
  signal: string
  signal_text: string
  close: number
  ma_key: string
  ma_val: number
  ma_deviation_pct: number
  base_price: number
  base_label: string
  atr?: number
  atr_pct?: number
  dynamic_spread: boolean
  grid_count: number
  grid_spread_pct: number
  step_pct: number
  lower_bound: number
  upper_bound: number
  current_grid: number
  total_grids: number
  position_ratio: number
  nearby_lower?: number
  nearby_upper?: number
  action_desc: string
}

export interface StockDataResponse {
  update_time: string
  symbol_name: string
  symbol: string
  start_date?: string
  end_date?: string
  dates: string[]
  kdata: number[][]
  volume: number[]
  MA5: number[]
  MA10: number[]
  MA20: number[]
  MA60: number[]
  MACD: number[]
  MACD_SIGNAL: number[]
  MACD_HIST: number[]
  K: number[]
  D: number[]
  J: number[]
  RSI: number[]
  BB_UPPER: number[]
  BB_MID: number[]
  BB_LOWER: number[]
  资金净流入: number[]
  累计净流入: number[]
  latest: LatestIndicator
  signals: string[][]
  grid_signals: Record<string, GridSignal>
  grid_signal: GridSignal
  trade_signal: string
}

export interface RealtimeData {
  name: string
  price: number
  prev_close: number
  change: number
  change_pct: number
  open: number
  high: number
  low: number
  volume: number
  amount: number
  date: string
  time: string
  source: string
}

export interface RealtimeResponse {
  code: number
  msg: string
  update_time: string
  data: Record<string, RealtimeData>
}

export interface SignalTimeRequest {
  symbol: string
  realtime_price: number
  prev_close?: number
}

export interface SignalTimeResponse {
  code: number
  msg: string
  symbol: string
  realtime_price: number
  prev_close: number
  change_pct: number
  trade_signal: string
  signals: string[][]
  grid_signals: Record<string, GridSignal>
  grid_signal: GridSignal
  latest: LatestIndicator
}

export interface NewsItem {
  title: string
  url: string
  time: string
  source: string
}

export interface NewsResponse {
  news: NewsItem[]
  update_time: string
}

export interface TradeRecord {
  entry_date: string
  entry_price: number
  entry_grid: number
  exit_date: string
  exit_price: number
  exit_grid: number
  shares: number
  pnl: number
  pnl_pct: number
}

export interface EquityPoint {
  date: string
  equity: number
}

export interface BacktestParams {
  grid_count: number
  spread_type: string
  base_ma_key: string
  position_size: number
  warmup_days: number
}

export interface BacktestRequest {
  symbol: string
  start_date?: string
  end_date?: string
  initial_capital: number
  grid_count: number
  spread_type: string
  base_ma_key: string
}

export interface SimulationAccount {
  initial_capital: number
  cash: number
  frozen_cash: number
  market_value: number
  total_assets: number
  unrealized_pnl: number
  realized_pnl: number
  total_pnl: number
}

export interface SimulationPosition {
  symbol: string
  name: string
  shares: number
  avg_cost: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  strategy_type: string
}

export interface SimulationOrder {
  id: string
  direction: string
  symbol: string
  name: string
  price: number
  shares: number
  commission: number
  timestamp: string
  pnl: number
  trade_type: string
}

export interface AutoTaskInfo {
  id: number
  symbol: string
  task_name: string
  strategy: string
  shares: number
  avg_cost: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  realized_pnl: number
  allocated_funds: number
  task_cash: number
  enabled: boolean
}

export interface AutoTasksSummary {
  task_count: number
  market_value: number
  unrealized_pnl: number
  realized_pnl: number
  tasks: AutoTaskInfo[]
}

export interface SimulationPortfolio {
  account: SimulationAccount
  positions: SimulationPosition[]
  orders: SimulationOrder[]
  auto_tasks: AutoTasksSummary
  total_return: number
  total_return_pct: number
}

export interface BacktestResponse {
  initial_capital: number
  final_equity: number
  total_return: number
  total_return_pct: number
  num_trades: number
  num_wins: number
  win_rate: number
  max_drawdown_pct: number
  equity_curve: EquityPoint[]
  trade_history: TradeRecord[]
  params: BacktestParams
}

export const stockService = {
  async getData(symbol: string, startDate?: string, endDate?: string): Promise<StockDataResponse> {
    const params = new URLSearchParams({ symbol })
    if (startDate) params.append('start_date', startDate)
    if (endDate) params.append('end_date', endDate)
    const response = await api.get<StockDataResponse>(`/data?${params}`)
    return response.data
  },

  async getRealtime(symbol: string): Promise<RealtimeResponse> {
    const response = await api.get<RealtimeResponse>(`/realtime?symbol=${symbol}`)
    return response.data
  },

  async getSignalTime(data: SignalTimeRequest): Promise<SignalTimeResponse> {
    const response = await api.post<SignalTimeResponse>('/signaltime', data)
    return response.data
  },

  async getNews(symbol?: string): Promise<NewsResponse> {
    const params = symbol ? `?symbol=${symbol}` : ''
    const response = await api.get<NewsResponse>(`/news${params}`)
    return response.data
  },

  async runBacktest(data: BacktestRequest): Promise<BacktestResponse> {
    const response = await api.post<BacktestResponse>('/backtest', data)
    return response.data
  },

  async runSimulation(data: BacktestRequest): Promise<BacktestResponse> {
    const response = await api.post<BacktestResponse>('/simulation', data)
    return response.data
  },

  async resetSimulation(userId: number, initialCapital: number): Promise<SimulationPortfolio> {
    const response = await api.post<SimulationPortfolio>('/simulation/reset', { user_id: userId, initial_capital: initialCapital })
    return response.data
  },

  async placeSimulationOrder(userId: number, direction: string, symbol: string, name: string, price: number, shares: number): Promise<any> {
    const response = await api.post<any>('/simulation/order', {
      user_id: userId,
      direction,
      symbol,
      name,
      price,
      shares
    })
    return response.data
  },

  async getSimulationPortfolio(): Promise<SimulationPortfolio> {
    const response = await api.get<SimulationPortfolio>('/simulation/portfolio')
    return response.data
  },

  async closeAllPositions(userId: number): Promise<any> {
    const response = await api.post<any>('/simulation/close', { user_id: userId })
    return response.data
  },

  async clearOrders(): Promise<any> {
    const response = await api.post<any>('/simulation/orders/clear', {})
    return response.data
  },

  async deletePosition(userId: number, symbol: string, strategy?: string): Promise<any> {
    const response = await api.delete<any>('/simulation/position', { data: { user_id: userId, symbol, strategy } })
    return response.data
  },

  async clearPositions(userId: number): Promise<any> {
    const response = await api.delete<any>('/simulation/positions', { data: { user_id: userId } })
    return response.data
  },

  async getSettings(): Promise<SimSettings> {
    const response = await api.get<SimSettings>('/settings')
    return response.data
  },

  async updateSettings(settings: SimSettings): Promise<SimSettings> {
    const response = await api.put<SimSettings>('/settings', settings)
    return response.data
  },

  async getSymbolSettings(symbol: string): Promise<SimSettings & { symbol: string }> {
    const response = await api.get<SimSettings & { symbol: string }>(`/settings/symbol/${symbol}`)
    return response.data
  },

  async getAllSymbolSettings(): Promise<Array<SimSettings & { symbol: string }>> {
    const response = await api.get<Array<SimSettings & { symbol: string }>>('/settings/symbols')
    return response.data
  },

  async upsertSymbolSettings(symbol: string, settings: Partial<SimSettings>): Promise<SimSettings & { symbol: string }> {
    const response = await api.put<SimSettings & { symbol: string }>(`/settings/symbol/${symbol}`, settings)
    return response.data
  },

  async deleteSymbolSettings(symbol: string): Promise<SimSettings & { symbol: string }> {
    const response = await api.delete<SimSettings & { symbol: string }>(`/settings/symbol/${symbol}`)
    return response.data
  },

  // ==================== Auto Trade (multi-task) ====================

  async getAutoTradeTasks(): Promise<TaskStatus[]> {
    const response = await api.get<TaskStatus[]>('/autotrade/tasks')
    return response.data
  },

  async getAutoTradeSummary(): Promise<AutoTradeSummary> {
    const response = await api.get<AutoTradeSummary>('/autotrade/summary')
    return response.data
  },

  async addAutoTradeTask(task: Partial<AutoTradeTask>): Promise<TaskStatus> {
    const response = await api.post<TaskStatus>('/autotrade/tasks', task)
    return response.data
  },

  async updateAutoTradeTask(taskId: number, config: Partial<AutoTradeTask>): Promise<TaskStatus> {
    const response = await api.put<TaskStatus>(`/autotrade/tasks/${taskId}`, config)
    return response.data
  },

  async deleteAutoTradeTask(taskId: number): Promise<any> {
    const response = await api.delete<any>(`/autotrade/tasks/${taskId}`)
    return response.data
  },

  async startAutoTradeTask(taskId: number): Promise<any> {
    const response = await api.post<any>(`/autotrade/tasks/${taskId}/start`, {})
    return response.data
  },

  async stopAutoTradeTask(taskId: number): Promise<any> {
    const response = await api.post<any>(`/autotrade/tasks/${taskId}/stop`, {})
    return response.data
  },

  async startAllAutoTradeTasks(): Promise<any> {
    const response = await api.post<any>('/autotrade/tasks/start-all', {})
    return response.data
  },

  async stopAllAutoTradeTasks(): Promise<any> {
    const response = await api.post<any>('/autotrade/tasks/stop-all', {})
    return response.data
  }
}

export interface SimSettings {
  commission_rate: number
  min_commission: number
  stamp_tax_rate: number
  transfer_fee_rate: number
}

export interface AutoTradeTask {
  id?: number
  user_id?: number
  enabled: boolean
  symbol: string
  strategy: string
  grid_count: number
  grid_spread: number
  base_ma_key: string
  macd_ma_key: string | null
  position_size: number
  check_interval: number
  allocated_funds: number
  last_check: string | null
  last_signal: string | null
  stop_loss_pct: number
  take_profit_pct: number
  trend_ma_key: string | null
  dynamic_interval: boolean
  max_drawdown_pct: number
  peak_value?: number
  consecutive_losses?: number
  use_multi_factor: boolean
  adaptive_strategy: boolean
}

export interface TaskStatus {
  id: number
  symbol: string
  running: boolean
  task: AutoTradeTask
  signal: GridSignal | null
  composite_score: CompositeScore | null
  task_cash: number
  task_pnl: number
  task_position: { shares: number; avg_cost: number }
  task_name: string
  unrealized_pnl: number
  realtime_price: number
  price_change_pct: number
  stock_name: string
}

export interface CompositeScore {
  score: number
  market_state: string
  market_state_cn: string
  signal: string
  position_suggestion: number
  factors: Record<string, number>
}

export interface AutoTradeSummary {
  total_allocated_funds: number
  total_task_cash: number
  total_position_value: number
  total_unrealized_pnl: number
  positions_by_symbol: Record<string, {
    symbol: string
    total_shares: number
    total_value: number
    tasks: Array<{
      id: number
      strategy: string
      shares: number
      avg_cost: number
      task_cash: number
      unrealized_pnl: number
    }>
  }>
  account_comparison: {
    account_cash: number
    account_market_value: number
    account_unrealized_pnl: number
    account_realized_pnl: number
    task_total_cash: number
    task_total_position_value: number
    task_total_unrealized_pnl: number
    cash_diff: number
    position_diff: number
    is_consistent: boolean
  } | null
  task_count: number
}

