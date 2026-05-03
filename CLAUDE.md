# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stock/ETF technical analysis platform. Provides K-line charts, technical indicators (MA, MACD, KDJ, RSI, Bollinger Bands), grid trading signals, simulation backtesting, multi-task auto-trading, and market news. Default symbol: 518880 (华夏黄金ETF).

## Running the App

**Backend (FastAPI)**:
```bash
cd D:/IdeaProject/gold_etf_web
python -m backend.main
```
Runs on http://localhost:8000

**Frontend (Vue 3 + Vite)**:
```bash
cd D:/IdeaProject/gold_etf_web/frontend
npm run dev
```
Runs on http://localhost:5173 (or next available port if in use), with `/api` proxied to FastAPI backend.

## Architecture

**前后端分离架构**: FastAPI backend serves pure JSON APIs; Vue 3 SPA calls APIs via axios.

### Frontend Structure (`frontend/src/`)

```
├── views/           # Page components (DashboardView, LoginView, RegisterView, SimulationView, SettingsView)
├── components/
│   ├── charts/      # ECharts wrappers (CandlestickChart, MacdChart, KdjChart, VolumeChart)
│   ├── trading/     # Trading UI (SignalBar, GridCard, SimulationCard, SignalGrid)
│   ├── simulation/  # Simulation trading (SimulationStats, SimulationConfig, PositionList,
│   │                #   SimulationOrderHistory, AutoTradePanel)
│   ├── search/      # SearchSection
│   ├── news/        # NewsSection
│   ├── layout/      # AppHeader
│   └── common/      # LoadingSpinner, CyberButton
├── stores/          # Pinia stores (auth.ts, stock.ts, simulation.ts)
├── services/       # API clients (api.ts, authService.ts, stockService.ts)
├── composables/    # Vue composables (useAuth, useClock, useRealtime, useGlobalSettings)
├── router/         # Vue Router with auth guards
└── utils/          # Utilities (symbol.ts - symbol normalization)
```

### Backend Structure (`backend/`)

```
├── main.py              # FastAPI entry point, all route handlers
├── core/security.py     # JWT token creation/verification, password hashing
├── models/
│   ├── user.py          # User model (SQLite)
│   ├── kline.py         # K-line cache model
│   ├── schemas.py       # Pydantic request/response models (HealthResponse, AuthResponse, etc.)
│   ├── simulation.py     # SimulationAccount, SimulationPosition, SimulationOrder (SQLite)
│   ├── settings.py      # SimSettings - commission/stamp_tax per symbol (SQLite)
│   └── auto_trade.py    # AutoTradeTask - per-symbol tasks with allocated_funds (SQLite)
├── services/
│   ├── gold_data.py     # Data fetch, caching, indicator calculation, signal generation
│   ├── grid_trade.py    # Grid trading strategy (MA/MACD-anchored modes)
│   ├── backtest.py      # Grid trading backtesting engine
│   ├── signal.py        # SignalSummary, get_trading_signal()
│   ├── news.py          # AKShare news + static fallback
│   ├── simulation_trade.py  # Trade execution, portfolio management, order history
│   └── auto_trade.py    # Multi-task auto-trading (asyncio loops per symbol per user)
└── utils/
    └── indicators.py    # Technical indicator calculations
```

### Database

SQLite in `instance/`:
- `users.db` — User accounts (passwords hashed with bcrypt)
- `stock_kline.db` — K-line cache
- `sim_trading.db` — Simulation trading: accounts, positions, orders, auto_trade_tasks, symbol_settings

## Key API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | User registration |
| POST | /api/auth/login | Login, returns JWT token |
| POST | /api/auth/logout | Logout (client-side token removal) |
| GET | /api/auth/me | Get current user |

### Data & Signals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/data | K-line data + indicators |
| GET | /api/realtime | Real-time price data |
| GET | /api/news | Market news |
| POST | /api/signaltime | Calculate signals for realtime price |
| POST | /api/backtest | Run grid trading backtest |

### Simulation Trading
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/simulation/reset | Reset account with initial capital |
| POST | /api/simulation/order | Place buy/sell order |
| GET | /api/simulation/portfolio | Get current portfolio |
| POST | /api/simulation/close | Close all positions |
| POST | /api/simulation/orders/clear | Clear all order history |

### Auto Trade (multi-task)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/autotrade/tasks | List all tasks |
| POST | /api/autotrade/tasks | Create task |
| PUT | /api/autotrade/tasks/{symbol} | Update task config |
| DELETE | /api/autotrade/tasks/{symbol} | Delete task |
| POST | /api/autotrade/tasks/{symbol}/start | Start task |
| POST | /api/autotrade/tasks/{symbol}/stop | Stop task |
| POST | /api/autotrade/tasks/start-all | Start all tasks |
| POST | /api/autotrade/tasks/stop-all | Stop all tasks |

### Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/settings | Get default commission settings |
| PUT | /api/settings | Update default settings |
| GET | /api/settings/symbols | List all symbol-specific settings |
| GET | /api/settings/symbol/{symbol} | Get symbol settings |
| PUT | /api/settings/symbol/{symbol} | Upsert symbol settings |
| DELETE | /api/settings/symbol/{symbol} | Delete symbol settings |

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

## Auto Trade Multi-task Architecture

- Each user can create multiple tasks (one per symbol)
- Each task has its own `allocated_funds` budget (virtual cash pool)
- Tasks share the same simulation account (cash/positions), but spending is tracked per-task via `_task_cash`
- P&L is tracked per-task via `_task_pnl` (realized) and `_task_positions` (shares/avg_cost)
- Global settings: `useGlobalSettings` composable stores `realtimeInterval`, `simRealtimeInterval`, `autoTradeInterval` in localStorage

## Important Notes

- K-line data: backend returns `[[open, close, low, high], ...]` but frontend accesses as `kdata[index][0-3]`
- Charts use `trigger: 'item'` for candlestick tooltip to work correctly with ECharts 6
- Auth store initializes `user` from localStorage on load (token is checked, user is restored if token exists)
- Grid sell threshold uses `grid_count - 2` (not `-1`) to trigger earlier profit-taking
- Charts color convention: **red (#ef5350) = price up**, **green (#26a69a) = price down**
- Frontend port: Vite defaults to 5173 but auto-increments if port is busy (check startup output)