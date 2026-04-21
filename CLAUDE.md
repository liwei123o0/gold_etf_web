# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stock/ETF technical analysis platform. Provides K-line charts, technical indicators (MA, MACD, KDJ, RSI, Bollinger Bands), grid trading signals, simulation backtesting, and market news. Default symbol: 518880 (华夏黄金ETF).

## Running the App

**Backend (FastAPI)**:
```bash
cd E:/project_ai/gold_etf_web
python -m backend.main
```
Runs on http://localhost:8000

**Frontend (Vue 3 + Vite)**:
```bash
cd E:/project_ai/gold_etf_web/frontend
npm run dev
```
Runs on http://localhost:5173 with `/api` proxied to FastAPI backend.

**Old Flask App** (legacy):
```bash
python app.py
```
Runs on port 5000. Uses Flask-Login instead of JWT.

## Architecture

**前后端分离架构**: FastAPI backend serves pure JSON APIs; Vue 3 SPA calls APIs via axios.

### Frontend Structure (`frontend/src/`)

```
├── views/           # Page components (DashboardView, LoginView, RegisterView)
├── components/
│   ├── charts/      # ECharts wrappers (CandlestickChart, MacdChart, KdjChart, VolumeChart)
│   ├── trading/     # Trading UI (SignalBar, GridCard, SimulationCard, SignalGrid)
│   ├── search/      # SearchSection
│   ├── news/        # NewsSection
│   ├── layout/      # AppHeader
│   └── common/      # LoadingSpinner, CyberButton
├── stores/          # Pinia stores (auth.ts, stock.ts)
├── services/       # API clients (api.ts, authService.ts, stockService.ts)
├── composables/    # Vue composables (useAuth, useClock, useRealtime, useECharts)
├── router/         # Vue Router with auth guards
└── utils/         # Utilities (symbol.ts - symbol normalization)
```

### Backend Structure (`backend/`)

```
├── main.py         # FastAPI entry point, all route handlers
├── core/security.py # JWT token creation/verification, password hashing
├── models/
│   ├── user.py     # User model (SQLite)
│   ├── kline.py    # K-line cache model
│   └── schemas.py  # Pydantic request/response models
├── services/
│   ├── gold_data.py    # Data fetch, caching, indicator calculation, signal generation
│   ├── grid_trade.py   # Grid trading strategy (MA/MACD-anchored modes)
│   ├── backtest.py     # Grid trading backtesting engine
│   ├── signal.py       # SignalSummary, get_trading_signal()
│   └── news.py         # AKShare news + static fallback
└── utils/
    └── indicators.py  # Technical indicator calculations (MA, MACD, KDJ, RSI, Bollinger, ATR, OBV, money flow)
```

### Database

SQLite in `instance/`:
- `users.db` — User accounts (passwords hashed with bcrypt)
- `stock_kline.db` — K-line cache

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | User registration |
| POST | /api/auth/login | Login, returns JWT token |
| GET | /api/auth/me | Get current user |
| GET | /api/data | K-line data + indicators |
| GET | /api/realtime | Real-time price data |
| GET | /api/news | Market news |
| POST | /api/backtest | Run grid trading backtest |
| POST | /api/signaltime | Calculate signals for realtime price |

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

## Important Notes

- K-line data: backend returns `[[open, close, low, high], ...]` but frontend accesses as `kdata[index][0-3]`
- Charts use `trigger: 'item'` for candlestick tooltip to work correctly with ECharts 6
- Auth store initializes `user` from localStorage on load (token is checked, user is restored if token exists)
- Grid sell threshold uses `grid_count - 2` (not `-1`) to trigger earlier profit-taking
- Charts color convention: **red (#ef5350) = price up**, **green (#26a69a) = price down**
