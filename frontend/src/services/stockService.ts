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
  }
}
