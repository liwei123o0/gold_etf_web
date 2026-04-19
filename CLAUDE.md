# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask web application for gold ETF technical analysis. Provides K-line charts, technical indicators (MA, MACD, KDJ, RSI, Bollinger Bands), grid trading signals, simulation backtesting, and gold market news. Default symbol: 518880 (华夏黄金ETF).

## Running the App

```bash
python app.py
```

Access at http://127.0.0.1:5000 (or 5001 if port 5000 is busy). First-time users must register. Production deployment uses gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Architecture

**前后端分离架构**: Backend (`backend/`) serves pure JSON APIs; frontend (`templates/` + `static/`) renders pages and calls APIs via JS.

### Backend Structure

```
backend/
├── routes/              # Flask blueprints - API endpoints
│   ├── auth.py          # /api/auth/* (register, login, logout, me)
│   ├── data.py          # /api/data (K-line data + indicators)
│   ├── news.py          # /api/news
│   └── backtest.py      # /api/backtest (simulation trading)
├── services/            # Business logic layer
│   ├── gold_data.py     # Core: data fetch, caching, indicator calc, signal gen
│   ├── grid_trade.py    # Grid trading strategy (MA/MACD-anchored modes)
│   ├── backtest.py      # Simulation backtesting engine
│   ├── signal.py        # SignalSummary class, text formatting
│   └── news.py          # AKShare news + static fallback
├── models/              # Data layer
│   ├── user.py          # User model (SQLite + Flask-Login)
│   └── kline.py        # K-line cache model
└── utils/
    └── indicators.py   # Technical indicator calculations
```

### Data Flow

1. `data.py` receives API request → validates symbol/date params
2. `gold_data.py` checks SQLite cache → fetches from Sina/QQ Finance if stale
3. `indicators.py` computes MA, MACD, KDJ, RSI, Bollinger, ATR, money flow, OBV
4. `gold_data.py` generates signals across multiple dimensions
5. `grid_trade.py` calculates grid levels for grid trading strategy
6. JSON response with kdata, indicators, signals, grid_signals

### Key Services

**gold_data.py**: Handles data source fallback (Sina primary → Tencent backup), cache strategy (INSERT OR REPLACE by symbol+date), and signal generation. Dynamic warmup period based on indicator needs.

**grid_trade.py**: Two modes — MA-anchored (baseline = MA5/10/20/60 ± ATR bands) and MACD-anchored (baseline = DIF or DEA). MACD mode includes dynamic grid width adjustment based on MACD_HIST 20-day mean.

**backtest.py**: Simulation backtesting engine for grid trading. Accepts grid_count (5/10/15/20), spread_type (fixed/atr), base_ma_key, initial_capital. Returns equity curve, trade history, win rate, max drawdown.

**signal.py**: `SignalSummary` aggregates latest indicators + signals. `get_trading_signal()` returns simplified BUY/SELL/HOLD based on scoring rules.

### Frontend

- `templates/stock.html` — Main analysis page with ECharts
- `static/js/main.js` — API calls, chart rendering, URL state sync, simulation UI
- `static/css/style.css` — Dark theme styling

### Database

SQLite in `instance/`:
- `users.db` — User accounts
- `stock_kline.db` — K-line cache

## Stock Symbol Normalization

| Input | Output | Rule |
|-------|--------|------|
| `518880` | `sh518880` | Auto-detect as Shanghai ETF |
| `000300` | `sz000300` | Auto-detect as Shenzhen index |
| `sh518880` | `sh518880` | Pass through |
| `6xxxxx` | `sh` prefix | Shanghai |
| `000xxx/002xxx/003xxx` | `sz` prefix | Shenzhen main/中小板 |
| `300xxx` | `sz` prefix | Shenzhen GEM |
| `8xxxxx` | `bj` prefix | Beijing |

## Signal Dimensions

System generates signals across multiple dimensions:

| Category | Signals |
|----------|---------|
| MA | 多头排列/空头排列/混乱, 金叉/死叉 |
| MACD | 强势/弱势/反弹/调整, 零轴上/零轴下 |
| KDJ | 超买/超卖/中性, 顶背离/底背离 |
| RSI | 超买/超卖/偏强/偏弱 |
| Bollinger | 上轨/下轨/偏强/偏弱 |
| Volume | 放量上涨/放量下跌/缩量整理 |
| Money Flow | 流入/流出 |
| Grid | 买入/卖出/持有/观望 |

综合建议基于 `trade_signal` 字段：买入/卖出/观望。

## Simulation Trading (模拟交易)

`POST /api/backtest` runs grid trading backtesting:

```json
{
    "symbol": "sh518880",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000,
    "grid_count": 10,
    "spread_type": "fixed",
    "base_ma_key": "MA20"
}
```

Returns: `total_return_pct`, `num_trades`, `win_rate`, `max_drawdown_pct`, `equity_curve`, `trade_history`.

## Important Notes

- K-line data format: backend returns `[[open, close, low, high], ...]` but ECharts expects `[open, close, low, high]` — frontend remaps `d[0], d[1], d[2], d[3]`
- `publisher.py` requires Node.js + wenyan CLI for WeChat public account publishing
- `scripts/daily_signal.py` — standalone script for generating daily signals
- JavaScript uses bracket notation for Chinese property names: `latest['收盘']` not `latest.收盘`
- Grid sell threshold uses `grid_count - 2` (not `-1`) to trigger earlier profit-taking
