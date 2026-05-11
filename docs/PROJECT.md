# 黄金ETF技术分析系统 — 项目说明文档

## 一、项目概述

黄金ETF技术分析系统是一个面向A股ETF/股票的全栈Web应用，提供K线数据展示、技术指标分析、网格交易信号、模拟交易、自动交易策略执行等功能。系统采用赛博朋克深色主题UI，支持多用户独立使用。

### 核心能力

| 能力 | 说明 |
|------|------|
| 技术分析 | K线图 + MA/MACD/KDJ/RSI/布林带/ATR 等多维度指标 |
| 交易信号 | 网格交易、MA趋势、布林带、RSI、MACD金叉死叉 5种策略信号 |
| 模拟交易 | 完整的模拟账户：下单、持仓、盈亏计算、手续费扣除 |
| 自动交易 | 后台调度器自动巡检 + 信号确认 + 自动下单 |
| 风控保护 | 止损止盈、最大回撤保护、连续亏损自适应冷却、交易日历校验 |
| 实时行情 | 新浪/Tushare/腾讯三源自动切换，实时价格推送 |
| 回测系统 | 基于历史数据的网格交易回测，输出收益率/胜率/最大回撤 |

---

## 二、技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 运行时 |
| FastAPI | 0.136 | Web框架 |
| SQLAlchemy | 2.0 | ORM |
| PostgreSQL | — | 数据库 |
| uvicorn | 0.46 | ASGI服务器 |
| pandas | 3.0 | 数据处理 |
| numpy | 2.4 | 数值计算 |
| tushare | 1.4.29 | A股数据源 |
| python-jose | 3.5 | JWT认证 |
| passlib | 1.7 | 密码哈希 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.5 | 前端框架（Composition API） |
| TypeScript | 6.0 | 类型安全 |
| Vite | 5.4 | 构建工具 |
| Pinia | 3.0 | 状态管理 |
| vue-router | 4.6 | 路由 |
| lightweight-charts | 5.1 | TradingView K线图 |
| echarts | 6.0 | 资金曲线等辅助图表 |
| axios | 1.15 | HTTP客户端 |
| sass | 1.99 | CSS预处理器 |

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────┐
│                    浏览器 (Vue 3 SPA)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ 看板页面  │ │ 模拟交易  │ │ 系统设置  │ │ 登录   │ │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘ └───┬────┘ │
│        └────────────┼────────────┼───────────┘      │
│                     ▼ Axios /api                     │
└─────────────────────┬───────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────┐
│               FastAPI 后端 (port 8000)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ 认证路由  │ │ 数据路由  │ │ 模拟交易  │ │自动交易│ │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘ └───┬────┘ │
│        └────────────┼────────────┼───────────┘      │
│                     ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │              服务层 (Services)                 │   │
│  │  gold_data / grid_trade / simulation_trade    │   │
│  │  auto_trade_scheduler / strategies / backtest │   │
│  └──────────────────┬───────────────────────────┘   │
│                     ▼                                │
│  ┌──────────────────────────────────────────────┐   │
│  │          数据层 (SQLAlchemy ORM)               │   │
│  │  users / sim_accounts / sim_positions         │   │
│  │  sim_orders / auto_trade_tasks / stock_kline  │   │
│  │  sim_settings / sim_symbol_settings           │   │
│  └──────────────────┬───────────────────────────┘   │
└─────────────────────┼───────────────────────────────┘
                      ▼
              ┌───────────────┐
              │  PostgreSQL   │
              └───────────────┘
```

---

## 四、项目目录结构

```
gold_etf_web/
├── backend/                         # 后端 Python 项目
│   ├── main.py                      # FastAPI 入口，所有API路由定义
│   ├── core/
│   │   └── security.py              # JWT 认证、密码哈希
│   ├── models/                      # 数据模型层 (SQLAlchemy ORM)
│   │   ├── db.py                    # 数据库连接、会话管理
│   │   ├── user.py                  # 用户模型 (users表)
│   │   ├── kline.py                 # K线数据模型 (stock_kline表)
│   │   ├── simulation.py            # 模拟交易模型 (账户/持仓/订单)
│   │   ├── settings.py              # 费率设置模型 (默认+单票)
│   │   ├── auto_trade.py            # 自动交易任务模型 (含迁移)
│   │   └── schemas.py               # Pydantic 请求/响应模型
│   ├── services/                    # 业务逻辑层
│   │   ├── gold_data.py             # 数据获取 (新浪/Tushare/腾讯)
│   │   ├── grid_trade.py            # 网格交易信号计算
│   │   ├── simulation_trade.py      # 模拟交易执行
│   │   ├── auto_trade.py            # 自动交易服务 (CRUD)
│   │   ├── auto_trade_scheduler.py  # 自动交易调度器 (核心)
│   │   ├── backtest.py              # 回测引擎
│   │   ├── signal.py                # 信号汇总
│   │   ├── news.py                  # 新闻获取
│   │   ├── publisher.py             # 信号发布
│   │   ├── auth.py                  # 认证服务
│   │   └── strategies/              # 策略工厂模式
│   │       ├── base.py              # 策略基类 (BaseStrategy)
│   │       ├── factory.py           # 策略工厂 (StrategyFactory)
│   │       ├── grid_strategy.py     # 网格交易策略
│   │       ├── ma_trend_strategy.py # MA趋势跟踪策略
│   │       ├── bollinger_strategy.py# 布林带均值回归策略
│   │       ├── rsi_strategy.py      # RSI超买超卖策略
│   │       └── macd_cross_strategy.py# MACD金叉死叉策略
│   ├── routes/                      # 路由模块 (部分功能拆分)
│   │   ├── realtime.py              # 实时行情路由
│   │   ├── signaltime.py            # 实时信号路由
│   │   ├── auth.py / data.py / ...  # 其他路由
│   ├── utils/                       # 工具模块
│   │   ├── timezone.py              # 中国时区处理
│   │   ├── indicators.py            # 技术指标计算 (MA/MACD/KDJ/RSI/BB/ATR)
│   │   └── symbol.py                # 股票代码格式化
│   └── logs/                        # 日志目录
│
├── frontend/                        # 前端 Vue 3 项目
│   ├── src/
│   │   ├── main.ts                  # 入口
│   │   ├── App.vue                  # 根组件
│   │   ├── router/index.ts          # 路由配置 + 守卫
│   │   ├── stores/                  # Pinia 状态管理
│   │   │   ├── auth.ts              # 认证状态
│   │   │   ├── stock.ts             # 股票数据状态
│   │   │   └── simulation.ts        # 模拟交易状态
│   │   ├── services/                # API 服务
│   │   │   ├── api.ts               # Axios 实例 (拦截器)
│   │   │   ├── authService.ts       # 认证 API
│   │   │   ├── stockService.ts      # 数据/模拟/自动交易 API + 类型
│   │   │   └── types.ts             # 认证类型定义
│   │   ├── composables/             # 组合函数
│   │   │   ├── useAuth.ts           # 认证逻辑
│   │   │   ├── useClock.ts          # 实时时钟
│   │   │   ├── useECharts.ts        # ECharts 封装
│   │   │   ├── useGlobalSettings.ts # 全局设置 (localStorage)
│   │   │   └── useRealtime.ts       # 实时数据轮询
│   │   ├── views/                   # 页面视图
│   │   │   ├── DashboardView.vue    # 看板页 (核心)
│   │   │   ├── SimulationView.vue   # 模拟交易页
│   │   │   ├── SettingsView.vue     # 系统设置页
│   │   │   ├── LoginView.vue        # 登录页
│   │   │   └── RegisterView.vue     # 注册页
│   │   ├── components/              # 组件
│   │   │   ├── charts/              # 图表 (K线/MACD/KDJ/成交量/资金曲线)
│   │   │   ├── trading/             # 交易 (信号条/网格卡片/指标摘要/信号网格/回测)
│   │   │   ├── simulation/          # 模拟交易 (统计/下单/持仓/记录/自动交易)
│   │   │   ├── layout/              # 布局 (导航栏)
│   │   │   ├── search/              # 搜索
│   │   │   ├── news/                # 新闻
│   │   │   └── common/              # 通用 (按钮/加载)
│   │   ├── utils/symbol.ts          # 股票代码工具
│   │   └── assets/styles/base.scss  # 全局样式 (赛博朋克主题)
│   ├── package.json
│   └── vite.config.ts               # Vite 配置 (代理到后端8000)
│
├── scripts/
│   └── daily_signal.py              # 每日信号提醒脚本 (cron定时)
└── requirements.txt                 # Python 依赖
```

---

## 五、数据库设计

### 5.1 users — 用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 用户ID |
| username | VARCHAR UNIQUE | 用户名 |
| password_hash | VARCHAR | 密码哈希 (werkzeug) |
| created_at | TIMESTAMP | 创建时间 |

### 5.2 sim_accounts — 模拟账户表

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | INTEGER PK | 用户ID |
| initial_capital | NUMERIC | 初始资金 |
| cash | NUMERIC | 可用资金 |
| frozen_cash | NUMERIC | 冻结资金 |
| realized_pnl | NUMERIC | 已实现盈亏 |
| created_at / updated_at | TIMESTAMP | 时间戳 |

### 5.3 sim_positions — 模拟持仓表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 持仓ID |
| user_id | INTEGER | 用户ID |
| symbol | VARCHAR | 股票代码 |
| name | VARCHAR | 股票名称 |
| shares | INTEGER | 持仓数量 |
| avg_cost | NUMERIC | 平均成本 |
| current_price | NUMERIC | 当前价格 |

### 5.4 sim_orders — 成交记录表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | VARCHAR PK | 订单ID (UUID) |
| user_id | INTEGER | 用户ID |
| direction | VARCHAR | 买入/卖出 |
| symbol | VARCHAR | 股票代码 |
| name | VARCHAR | 股票名称 |
| price | NUMERIC | 成交价格 |
| shares | INTEGER | 成交数量 |
| commission | NUMERIC | 手续费 |
| pnl | NUMERIC | 盈亏 |
| trade_type | VARCHAR | manual/auto |
| timestamp | TIMESTAMP | 成交时间 |

### 5.5 auto_trade_tasks — 自动交易任务表

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| id | SERIAL PK | 自增 | 任务ID |
| user_id | INTEGER | — | 用户ID |
| symbol | VARCHAR | — | 股票代码 |
| strategy | VARCHAR | grid | 策略类型 |
| grid_count | INTEGER | 10 | 网格数量 |
| grid_spread | NUMERIC | 0.10 | 网格间距(%) |
| base_ma_key | VARCHAR | MA20 | 基准均线 |
| macd_ma_key | VARCHAR | NULL | MACD均线 |
| position_size | NUMERIC | 1.0 | 仓位大小(0-1) |
| check_interval | INTEGER | 30 | 检查间隔(秒) |
| allocated_funds | NUMERIC | 0 | 分配资金 |
| enabled | BOOLEAN | FALSE | 是否启用 |
| stop_loss_pct | NUMERIC | -5.0 | 止损百分比 |
| take_profit_pct | NUMERIC | 10.0 | 止盈百分比 |
| trend_ma_key | VARCHAR | NULL | 趋势均线 |
| dynamic_interval | BOOLEAN | FALSE | 动态间隔 |
| cooldown_seconds | INTEGER | 60 | 冷却时间(秒) |
| max_daily_trades | INTEGER | 50 | 每日最大交易次数 |
| max_drawdown_pct | NUMERIC | -15.0 | 最大回撤阈值(%) |
| peak_value | NUMERIC | 0 | 历史净值峰值 |
| consecutive_losses | INTEGER | 0 | 连续亏损次数 |
| last_check | TIMESTAMP | NULL | 最后检查时间 |
| last_signal | VARCHAR | NULL | 最后信号 |
| last_trade_time | TIMESTAMP | NULL | 最后交易时间 |
| last_trade_direction | VARCHAR | NULL | 最后交易方向 |
| trade_count_today | INTEGER | 0 | 今日交易次数 |
| last_trade_date | VARCHAR | NULL | 最后交易日期 |
| consecutive_signals | INTEGER | 0 | 连续信号计数 |
| created_at / updated_at | TIMESTAMP | — | 时间戳 |

**唯一约束**: `uq_user_symbol_strategy` (user_id, symbol, strategy)

### 5.6 stock_kline — K线缓存表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 记录ID |
| symbol | VARCHAR | 股票代码 |
| date | DATE | 交易日期 |
| open / high / low / close | NUMERIC | OHLC |
| volume | NUMERIC | 成交量 |

**唯一约束**: `uq_stock_kline_symbol_date` (symbol, date)

### 5.7 sim_settings / sim_symbol_settings — 费率设置表

| 字段 | 类型 | 说明 |
|------|------|------|
| commission_rate | NUMERIC | 佣金费率 (默认0.0003) |
| min_commission | NUMERIC | 最低佣金 (默认5.0) |
| stamp_tax_rate | NUMERIC | 印花税率 (默认0.001) |
| transfer_fee_rate | NUMERIC | 过户费率 (默认0.00002) |

---

## 六、API 接口总览

### 6.1 认证模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 (返回JWT) |
| POST | `/api/auth/logout` | 用户登出 |
| GET | `/api/auth/me` | 获取当前用户 |

### 6.2 数据模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data?symbol=&start_date=&end_date=` | 获取K线+技术指标 |
| GET | `/api/realtime?symbol=` | 获取实时行情 |
| POST | `/api/signaltime` | 根据实时价格计算信号 |
| GET | `/api/news?symbol=` | 获取新闻 |

### 6.3 回测模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/backtest` | 运行网格交易回测 |
| POST | `/api/simulation` | 运行模拟 (同回测) |

### 6.4 模拟交易模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/simulation/reset` | 重置模拟账户 |
| POST | `/api/simulation/order` | 下单买入/卖出 |
| GET | `/api/simulation/portfolio` | 获取投资组合 |
| POST | `/api/simulation/close` | 全部清仓 |
| POST | `/api/simulation/orders/clear` | 清空成交记录 |

### 6.5 系统设置模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取默认费率 |
| PUT | `/api/settings` | 更新默认费率 |
| GET | `/api/settings/symbols` | 获取所有单票费率 |
| GET | `/api/settings/symbol/{symbol}` | 获取单票费率 |
| PUT | `/api/settings/symbol/{symbol}` | 设置单票费率 |
| DELETE | `/api/settings/symbol/{symbol}` | 删除单票费率 |

### 6.6 自动交易模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/autotrade/tasks` | 获取所有任务 |
| POST | `/api/autotrade/tasks` | 新增任务 |
| PUT | `/api/autotrade/tasks/{id}` | 更新任务配置 |
| DELETE | `/api/autotrade/tasks/{id}` | 删除任务 |
| POST | `/api/autotrade/tasks/{id}/start` | 启动任务 |
| POST | `/api/autotrade/tasks/{id}/stop` | 停止任务 |
| POST | `/api/autotrade/tasks/start-all` | 全部启动 |
| POST | `/api/autotrade/tasks/stop-all` | 全部停止 |
| GET | `/api/autotrade/strategies` | 获取可用策略列表 |

---

## 七、自动交易调度器架构

### 核心流程

```
AutoTradeScheduler._run_loop()
    │
    ├── 每隔 N 秒执行一轮
    │
    └── _check_all_tasks()
         │
         ├── 1. 查询所有 enabled=True 的任务
         ├── 2. 预加载所有 symbol 的行情数据 (缓存去重)
         ├── 3. 判断是否交易时间 (Tushare交易日历 + 时段判断)
         │
         └── 对每个任务:
              │
              ├── 交易时间 → _check_and_trade()
              │    ├── 获取模拟账户持仓/资金
              │    ├── 计算任务净值 → 最大回撤检查
              │    ├── 止损/止盈检查
              │    ├── 计算交易信号 (StrategyFactory)
              │    ├── 趋势过滤 (可选)
              │    ├── 连续信号确认 (需连续2次相同)
              │    ├── 冷却期检查 (自适应: 60s→120s→180s→300s)
              │    ├── 每日交易次数检查
              │    ├── 计算仓位偏差 → 最小调仓阈值
              │    └── 执行下单 → 更新持仓/连续亏损
              │
              └── 非交易时间 → _update_check_time() (仅更新信号)
```

### 5种交易策略

| 策略 | 标识 | 逻辑 |
|------|------|------|
| 网格交易 | `grid` | 价格偏离均线 → 按网格步长分批买入/卖出 |
| MA趋势跟踪 | `ma_trend` | 快线上穿慢线 → 买入，下穿 → 卖出 |
| 布林带均值回归 | `bollinger` | 价格触及下轨 → 买入，触及上轨 → 卖出 |
| RSI超买超卖 | `rsi` | RSI<30 → 买入，RSI>70 → 卖出 |
| MACD金叉死叉 | `macd_cross` | DIF上穿DEA → 买入，下穿 → 卖出 |

### 风控机制

| 机制 | 说明 |
|------|------|
| 止损/止盈 | 持仓盈亏达到阈值自动清仓 |
| 最大回撤保护 | 净值从峰值回撤超过阈值(默认-15%)自动暂停任务 |
| 连续亏损自适应冷却 | 连续亏损1次→120s, 2次→180s, 3次+→300s冷却 |
| 每日交易次数限制 | 默认50次/天 |
| 连续信号确认 | 信号需连续2次相同才执行交易 |
| 趋势过滤 | 可选：价格低于趋势均线时不买入，高于时不卖出 |
| 交易日历 | 集成Tushare交易日历，法定节假日不交易 |
| 动态间隔 | 根据ATR波动率自动调整检查频率 |

---

## 八、数据源架构

```
gold_data.get_full_data()
    │
    ├── 1. 查询 PostgreSQL 缓存 (stock_kline)
    │    └── 有缓存且未过期 → 直接返回
    │
    └── 2. 缓存未命中 → _fetch_from_network()
         │
         ├── 新浪财经 (3次重试) ──→ 成功则缓存到DB
         │
         ├── Tushare (1次) ──────→ 成功则缓存到DB
         │
         └── 腾讯财经 (3次重试) ──→ 成功则缓存到DB
```

---

## 九、部署说明

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- 操作系统: Windows/Linux/macOS

### 后端启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置数据库 (修改 backend/models/db.py 中的 DB_CONFIG)
DB_CONFIG = {
    "dbname": "database",
    "user": "root",
    "password": "root",
    "host": "localhost",
    "port": "5432",
}

# 3. 启动后端
cd backend
python main.py
# 或
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端启动

```bash
# 1. 安装依赖
cd frontend
npm install

# 2. 开发模式
npm run dev
# 访问 http://localhost:5174

# 3. 生产构建
npm run build
```

### 数据库初始化

应用启动时自动执行：
1. `Base.metadata.create_all()` — 创建所有表
2. `AutoTradeTask.migrate_schema()` — 增量添加新列（安全可重复执行）

### 定时任务 (可选)

```bash
# 每日信号提醒 (cron)
35 9 * * 1-5 cd /path/to/gold_etf_web && python scripts/daily_signal.py >> logs/daily_signal.log 2>&1
```
