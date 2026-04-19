# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask web application for gold ETF technical analysis. Provides K-line charts, technical indicators (MA, MACD, KDJ, RSI, Bollinger Bands), grid trading signals, and gold market news. Default symbol: 518880 (华夏黄金ETF).

## Running the App

```bash
python app.py
```

Access at http://127.0.0.1:5000. First-time users must register. Production deployment uses gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Architecture

**前后端分离架构**: Backend (`backend/`) serves pure JSON APIs; frontend (`templates/` + `static/`) renders pages and calls APIs via JS.

### Backend Structure

```
backend/
├── routes/          # Flask blueprints - API endpoints
│   ├── auth.py      # /api/auth/* (register, login, logout, me)
│   ├── data.py      # /api/data (K-line data + indicators)
│   └── news.py      # /api/news
├── services/        # Business logic layer
│   ├── gold_data.py # Core: data fetch, caching, indicator calc, signal gen
│   ├── grid_trade.py# Grid trading strategy (MA/MACD-anchored modes)
│   ├── signal.py    # SignalSummary class, text formatting
│   └── news.py      # AKShare news + static fallback
├── models/          # Data layer
│   ├── user.py      # User model (SQLite + Flask-Login)
│   └── kline.py     # K-line cache model
└── utils/
    └── indicators.py # Technical indicator calculations (MA, MACD, KDJ, RSI, BB, etc.)
```

### Data Flow

1. `data.py` receives API request → validates symbol/date params
2. `gold_data.py` checks SQLite cache → fetches from Sina/QQ Finance if stale
3. `indicators.py` computes MA, MACD, KDJ, RSI, Bollinger, money flow
4. `gold_data.py` generates signals → `grid_trade.py` calculates grid levels
5. JSON response with kdata, indicators, signals, grid_signals

### Key Services

**gold_data.py**: Handles data source fallback (Sina primary → Tencent backup), cache strategy (INSERT OR REPLACE by symbol+date), and signal generation across 6 dimensions.

**grid_trade.py**: Two modes — MA-anchored (baseline = MA5/10/20/60 ± ATR bands) and MACD-anchored (baseline = DIF or DEA). MACD mode includes dynamic grid width adjustment based on MACD_HIST 20-day mean.

**signal.py**: `SignalSummary` aggregates latest indicators + signals. `get_trading_signal()` returns simplified BUY/SELL/HOLD based on scoring rules.

### Frontend

- `templates/stock.html` — Main analysis page (ECharts for charts)
- `static/js/main.js` — API calls, chart rendering, URL state sync
- `static/css/style.css` — Dark theme styling

### Database

SQLite in `instance/`:
- `users.db` — User accounts (id, username, password_hash, created_at)
- `stock_kline.db` — K-line cache (symbol, date, open, high, low, close, volume)

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

System generates signals from 6 dimensions: MA多头/空头, MACD强势/弱势/反弹/调整, KDJ超买/超卖, RSI超买/超卖, 资金流入/流出. 综合建议: 看涨>看跌+2 → 偏多, 看跌>看涨+2 → 偏空, 其他 → 震荡整理.

## Important Notes

- K-line data format: backend returns `[[open, close, low, high], ...]` but ECharts expects `[open, close, low, high]` — frontend remaps `d[0], d[1], d[2], d[3]`
- `publisher.py` requires Node.js + wenyan CLI for WeChat public account publishing
- `scripts/daily_signal.py` — standalone script for generating daily signals
