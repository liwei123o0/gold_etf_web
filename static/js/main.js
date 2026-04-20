/**
 * 黄金ETF技术分析系统 - 前端主脚本
 * 负责数据加载、图表渲染、新闻展示、搜索表单
 */

// ========== 全局状态 ==========
let chartInstances = {};
let currentUser = null;
let currentSymbol = 'sh518880';
let _chartDates = [];  // 存储日期数组
let _chartKdata = [];  // 存储K线数据 [开盘, 收盘, 最低, 最高]
let _cachedData = null;  // 缓存最近一次API响应，供均线切换时直接重算

// ========== 实时时钟 ==========
function updateClock() {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    const year = now.getFullYear();
    const month = pad(now.getMonth() + 1);
    const day = pad(now.getDate());
    const hour = pad(now.getHours());
    const minute = pad(now.getMinutes());
    const second = pad(now.getSeconds());
    document.getElementById('realtimeClock').textContent =
        `${year}年${month}月${day}日 ${hour}:${minute}:${second}`;
}

// ========== 实时行情轮询 ==========
let _realtimeInterval = null;

async function loadRealtimePrice() {
    try {
        const resp = await fetch(`/api/realtime?symbol=${currentSymbol}`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (data.code !== 0 || !data.data) return;

        const item = data.data[currentSymbol];
        if (!item || !item.price) return;

        renderRealtimePrice(item);

        // 更新今日K线到图表
        updateTodayCandle(item);

        // 用实时价格重新计算交易信号
        loadRealtimeSignal(item.price, item.prev_close);
    } catch (e) {
        console.warn('实时数据获取失败:', e.message);
    }
}

/**
 * 用实时行情更新今日K线（蜡烛图最后一根）
 * 规则：今日K线用 realtime 的 open/high/low/price(close)
 * 若图表最后一根不是今天，则追加今日K线
 */
function updateTodayCandle(item) {
    const mainChart = chartInstances.main;
    if (!mainChart || !item) return;

    const todayStr = item.date; // 'YYYY-MM-DD'
    if (!todayStr) return;

    // 找到今日在日期列表中的位置
    let todayIdx = _chartDates.indexOf(todayStr);

    if (todayIdx === -1) {
        // 图表里没有今天 → 追加一根新K线
        _chartDates.push(todayStr);
        _chartKdata.push([item.open, item.price, item.low, item.high]);
        todayIdx = _chartKdata.length - 1;
    } else {
        // 更新今日K线（取实际OHLC）
        _chartKdata[todayIdx] = [item.open, item.price, item.low, item.high];
    }

    // 更新主图 series[0] (K线)
    const candlestickData = _chartKdata.map(d => [d[0], d[1], d[2], d[3]]);
    mainChart.setOption({
        xAxis: { data: _chartDates },
        series: [{ name: 'K线', data: candlestickData }]
    });
}

async function loadRealtimeSignal(realtimePrice, prevClose) {
    try {
        const resp = await fetch('/api/signaltime', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: currentSymbol,
                realtime_price: realtimePrice,
                prev_close: prevClose || undefined,
            })
        });
        if (!resp.ok) return;
        const result = await resp.json();
        if (result.code !== 0) return;

        // 用实时信号更新信号栏（使用当前选中的均线）
        const maSelectEl = document.getElementById('gridMaSelect');
        const maKey = maSelectEl ? maSelectEl.value.toUpperCase() : 'MA20';
        renderTradeSignal(result, maKey);
        renderGridCardFromRealtime(result);
        updateAdvice(result, maKey);
    } catch (e) {
        console.warn('实时信号计算失败:', e.message);
    }
}

function renderGridCardFromRealtime(data) {
    const card = document.getElementById('gridCard');
    if (!card) return;

    const gridSignals = data.grid_signals || {};
    const selectEl = document.getElementById('gridMaSelect');
    const maKey = selectEl ? selectEl.value.toUpperCase() : 'MA20';
    const grid = gridSignals[maKey] || data.grid_signal || {};
    if (!grid || !grid.close) return;

    const n = grid.total_grids || 10;
    const cur = grid.current_grid || 0;
    const action = grid.signal || '持有';

    // 卡片颜色
    card.className = 'grid-card';
    if (action === '买入') card.classList.add('signal-buy');
    else if (action === '卖出') card.classList.add('signal-sell');
    else card.classList.add('signal-hold');

    // 动态/静态标签
    const badgeEl = document.getElementById('gridDynamicBadge');
    if (grid.dynamic_spread) {
        badgeEl.textContent = 'ATR动态';
        badgeEl.className = 'grid-dynamic-badge';
    } else {
        badgeEl.textContent = '固定参数';
        badgeEl.className = 'grid-dynamic-badge static';
    }

    // 参数区
    document.getElementById('gridPrice').textContent = grid.close?.toFixed(4) || '-';
    document.getElementById('gridSpread').textContent = `±${grid.grid_spread_pct?.toFixed(1)}%`;
    document.getElementById('gridStep').textContent = `${grid.step_pct?.toFixed(2)}%/格`;

    const atrEl = document.getElementById('gridATR');
    if (grid.atr) {
        atrEl.textContent = `${grid.atr.toFixed(4)} (${grid.atr_pct?.toFixed(2)}%)`;
        atrEl.style.color = '#667eea';
    } else {
        atrEl.textContent = '无数据';
        atrEl.style.color = '#555';
    }

    const ma20DevEl = document.getElementById('gridMA20Dev');
    if (grid.ma_deviation_pct !== undefined && grid.ma_deviation_pct !== null) {
        const dev = grid.ma_deviation_pct;
        ma20DevEl.textContent = `${dev > 0 ? '+' : ''}${dev.toFixed(2)}%`;
        ma20DevEl.style.color = dev > 0 ? '#26a69a' : '#ef5350';
    } else {
        ma20DevEl.textContent = '-';
        ma20DevEl.style.color = '#555';
    }

    const posPct = Math.round((grid.position_ratio || 0) * 100);
    const posEl = document.getElementById('gridPosition');
    posEl.textContent = `${posPct}%`;
    posEl.style.color = posPct >= 70 ? '#26a69a' : posPct >= 40 ? '#FF9800' : '#ef5350';

    // 网格可视化条
    const visualEl = document.getElementById('gridVisual');
    let barCells = '';
    for (let i = 0; i < n; i++) {
        const filled = i < cur ? 'filled' : '';
        const current = i === cur ? 'current' : '';
        barCells += `<div class="grid-bar-cell ${filled} ${current}"></div>`;
    }
    const pointerLeft = n > 0 ? ((cur + 0.5) / n * 100) : 50;
    visualEl.innerHTML = `
        <div class="grid-bar-wrapper">
            <div class="grid-bar-bg">${barCells}</div>
            <div class="grid-bar-pointer" style="left:${pointerLeft}%"></div>
        </div>
        <div class="grid-labels">
            <span>${grid.lower_bound?.toFixed(3)} (底)</span>
            <span>${grid.upper_bound?.toFixed(3)} (顶)</span>
        </div>
    `;

    // 底部建议
    const footerEl = document.getElementById('gridFooter');
    const emoji = {'买入': '📈', '卖出': '📉', '持有': '➡️'}[action] || '➡️';
    const cls = {'买入': 'action-buy', '卖出': 'action-sell', '持有': 'action-hold'}[action] || 'action-hold';
    footerEl.innerHTML = `${emoji} <span class="${cls}">${action}</span>：${grid.action_desc || ''} &nbsp;|&nbsp; 📍 第${cur}格/共${n}格`;
}

function renderRealtimePrice(item) {
    const priceEl = document.getElementById('rtPrice');
    const changeEl = document.getElementById('rtChange');
    const nameEl = document.getElementById('rtName');
    const sourceEl = document.getElementById('rtSource');
    const containerEl = document.getElementById('realtimePrice');

    if (!priceEl) return;

    // 显示容器
    containerEl.style.display = 'inline-flex';
    containerEl.style.alignItems = 'center';

    // 名称
    if (nameEl) nameEl.textContent = item.name || '';

    // 价格
    if (priceEl) {
        priceEl.textContent = item.price.toFixed(3);
    }

    // 涨跌
    if (changeEl) {
        const change = item.change || 0;
        const changePct = item.change_pct || 0;
        const sign = change >= 0 ? '+' : '';
        changeEl.textContent = `${sign}${change.toFixed(3)} (${sign}${changePct.toFixed(2)}%)`;

        // 颜色：涨=red( ef5350)，跌=green( 26a69a)，正好跟A股颜色一致
        if (change > 0) {
            changeEl.className = 'rt-change up';
        } else if (change < 0) {
            changeEl.className = 'rt-change down';
        } else {
            changeEl.className = 'rt-change flat';
        }
    }

    // 数据来源
    if (sourceEl) {
        sourceEl.textContent = item.time ? `(${item.source} ${item.time})` : `(${item.source})`;
    }

    // 同时更新指标卡片中的最新价
    updateLatestPriceCard(item);
}

function updateLatestPriceCard(item) {
    const cardsEl = document.getElementById('summaryCards');
    if (!cardsEl) return;

    const firstCard = cardsEl.querySelector('.card');
    if (!firstCard) return;

    const valueEl = firstCard.querySelector('.value');
    const changeEl = firstCard.querySelector('.change');

    if (valueEl) {
        valueEl.textContent = item.price.toFixed(3);
    }
    if (changeEl) {
        const changePct = item.change_pct || 0;
        changeEl.textContent = `${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%`;
        changeEl.className = `change ${changePct >= 0 ? 'up' : 'down'}`;
    }
}

function startRealtimePolling(intervalMs = 60000) {
    // 先立即加载一次
    loadRealtimePrice();
    // 再定时
    if (_realtimeInterval) clearInterval(_realtimeInterval);
    if (intervalMs <= 0) return; // 手动模式不自动轮询
    _realtimeInterval = setInterval(loadRealtimePrice, intervalMs);
}

function stopRealtimePolling() {
    if (_realtimeInterval) {
        clearInterval(_realtimeInterval);
        _realtimeInterval = null;
    }
}

function onRealtimeIntervalChange() {
    const select = document.getElementById('realtimeIntervalSelect');
    if (!select) return;
    const ms = parseInt(select.value, 10);
    // 更新调用处传入正确参数
    if (ms <= 0) {
        stopRealtimePolling();
        document.getElementById('realtimeStatus').textContent = '手动模式';
    } else {
        startRealtimePolling(ms);
        document.getElementById('realtimeStatus').textContent = `自动刷新 ${ms/1000}秒`;
    }
}

// ========== 用户状态 ==========
async function loadUserStatus() {
    try {
        const resp = await fetch('/api/auth/me');
        const data = await resp.json();
        currentUser = data.user;
        renderUserStatus();
    } catch (e) {
        currentUser = null;
        renderUserStatus();
    }
}

function renderUserStatus() {
    const el = document.getElementById('userStatus');
    if (!el) return;
    if (currentUser) {
        el.innerHTML = `
            <span class="username-text">👤 ${currentUser.username}</span>
            <span class="topbar-sep">|</span>
            <button class="btn-logout" onclick="logout()">退出</button>
        `;
    } else {
        el.innerHTML = `
            <a href="/auth/login" class="topbar-link">登录</a>
            <span class="topbar-sep">|</span>
            <a href="/auth/register" class="topbar-link">注册</a>
        `;
    }
}

async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
        currentUser = null;
        renderUserStatus();
        window.location.href = '/';
    } catch (e) {
        console.error('登出失败:', e);
    }
}

// ========== 搜索 & 日期工具 ==========

/**
 * 符号规范化：纯数字 -> 带前缀
 * Examples: '518880' -> 'sh518880', '000300' -> 'sz000300'
 */
function normalizeSymbol(raw) {
    raw = (raw || '').trim().toLowerCase();
    if (!raw) return 'sh518880';
    // 已是完整代码
    if (raw.startsWith('sh') || raw.startsWith('sz')) return raw;
    // 去掉可能的 cn_ 前缀
    if (raw.startsWith('cn_')) raw = raw.slice(3);

    // ========== 数字代码自动前缀识别 ==========
    // 6xxxxx -> 上海 (沪市主板 600/601/603 + 科创板 688)
    if (/^6\d{5}$/.test(raw)) return 'sh' + raw;
    // 000xxx -> 深圳 (沪深300等指数)
    if (/^000\d{3}$/.test(raw)) return 'sz' + raw;
    // 001xxx -> 深圳
    if (/^001\d{3}$/.test(raw)) return 'sz' + raw;
    // 002xxx -> 深圳 (中小板)
    if (/^002\d{3}$/.test(raw)) return 'sz' + raw;
    // 003xxx -> 深圳
    if (/^003\d{3}$/.test(raw)) return 'sz' + raw;
    // 300xxx -> 创业板，深圳
    if (/^300\d{3}$/.test(raw)) return 'sz' + raw;
    // 8xxxxx -> 北交所 (新三板精选层)
    if (/^8\d{5}$/.test(raw)) return 'bj' + raw;

    // 默认上海
    return 'sh' + raw;
}

/** 格式 YYYY-MM-DD */
function fmtDate(d) {
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}

/** 设置日期范围快捷按钮高亮 */
function highlightQuickBtn(months) {
    document.querySelectorAll('.quick-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const btn = document.querySelector(`.quick-btn[onclick="setDateRange(${months})"]`);
    if (btn) btn.classList.add('active');
}

/**
 * 设置日期输入框为最近 N 个月，并自动搜索
 * @param {number} months
 */
function setDateRange(months) {
    highlightQuickBtn(months);
    const end = new Date();
    const start = new Date();
    start.setMonth(start.getMonth() - months);
    document.getElementById('startDateInput').value = fmtDate(start);
    document.getElementById('endDateInput').value = fmtDate(end);
    // 自动触发搜索
    doSearch();
}

/** 表单提交：阻止跳转，直接 AJAX 加载数据 */
function handleSearch(event) {
    event.preventDefault();
    doSearch();
    return false;
}

/** 执行搜索 */
function doSearch() {
    const codeInput = document.getElementById('stockCodeInput');
    const startInput = document.getElementById('startDateInput');
    const endInput = document.getElementById('endDateInput');

    let code = normalizeSymbol(codeInput.value.trim());
    if (!codeInput.value.trim()) {
        // 空输入默认用当前
        code = currentSymbol;
    }

    const startDate = startInput.value || null;
    const endDate = endInput.value || null;

    loadStockData(code, startDate, endDate);
}

// ========== 数据加载 ==========

/**
 * 加载个股数据并渲染全图表
 * @param {string} code   规范化后的股票代码，如 sh518880
 * @param {string|null} startDate  YYYY-MM-DD
 * @param {string|null} endDate    YYYY-MM-DD
 */
async function loadStockData(code, startDate, endDate) {
    showLoading(true);

    try {
        // 切换标的时先停止旧轮询
        stopRealtimePolling();

        // 构造 URL 参数
        let url = `/api/data?symbol=${encodeURIComponent(code)}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate)   url += `&end_date=${endDate}`;

        const resp = await fetch(url);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ error: '加载失败' }));
            throw new Error(err.error || `HTTP ${resp.status}`);
        }
        const data = await resp.json();

        // 更新当前状态
        currentSymbol = code;

        // 更新页面标题
        updatePageTitle(code, data.symbol_name);

        // 更新股票信息栏
        updateStockBar(code, data.symbol_name, startDate, endDate);

        // 渲染图表和分析
        renderSummary(data);
        const maSelectEl = document.getElementById('gridMaSelect');
        const maKey = maSelectEl ? maSelectEl.value.toUpperCase() : 'MA20';
        renderSignals(data, maKey);
        renderTradeSignal(data, maKey);
        renderGridCard(data);
        // 缓存数据供均线切换时直接重算
        _cachedData = data;
        renderCharts(data);

        // 更新时间戳
        const updateEl = document.getElementById('updateTime');
        if (updateEl) updateEl.textContent = data.update_time || '-';

        // 更新ETF介绍和新闻标题
        updateInfoSection(code, data.symbol_name);
        updateNewsTitle(code);

        // 同步更新新闻
        loadNews(code);

        // 更新 URL（不跳转）
        updateURL(code, startDate, endDate);

        // 启动实时行情轮询（默认1分钟）
        const intervalSelect = document.getElementById('realtimeIntervalSelect');
        const ms = intervalSelect ? parseInt(intervalSelect.value, 10) : 60000;
        startRealtimePolling(ms);

    } catch (e) {
        console.error('数据加载失败:', e);
        const cardsEl = document.getElementById('summaryCards');
        if (cardsEl) cardsEl.innerHTML = `<div class="loading" style="color:#ef5350">数据加载失败: ${e.message}</div>`;
        const signalEl = document.getElementById('signalGrid');
        if (signalEl) signalEl.innerHTML = `<div class="loading" style="color:#ef5350">加载失败</div>`;
        const adviceEl = document.getElementById('finalAdvice');
        if (adviceEl) adviceEl.innerHTML = `<div class="loading" style="color:#ef5350">加载失败</div>`;
    } finally {
        showLoading(false);
    }
}

// ========== 页面更新 ==========

function updatePageTitle(code, name) {
    const titleEl = document.getElementById('pageTitle');
    const headerEl = document.getElementById('headerTitle');
    if (titleEl) titleEl.textContent = `${name || code} 技术分析`;
    if (headerEl) headerEl.textContent = `📊 ${name || code} 技术分析系统`;
}

function updateStockBar(code, name, startDate, endDate) {
    const bar = document.getElementById('currentStockBar');
    const codeEl = document.getElementById('displayCode');
    const nameEl = document.getElementById('displayName');
    const rangeEl = document.getElementById('displayRange');
    if (!bar) return;
    bar.style.display = 'flex';
    if (codeEl) codeEl.textContent = code.toUpperCase();
    if (nameEl) nameEl.textContent = name || code;
    if (rangeEl) {
        if (startDate && endDate) {
            rangeEl.textContent = `${startDate} ~ ${endDate}`;
        } else {
            rangeEl.textContent = '默认范围（近90天）';
        }
    }
}

function updateURL(code, startDate, endDate) {
    let url = `/stock?symbol=${encodeURIComponent(code)}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate)   url += `&end_date=${endDate}`;
    window.history.replaceState({}, '', url);
}

// ========== 动态内容更新 ==========
function updateInfoSection(code, name) {
    const section = document.getElementById('infoSection');
    if (!section) return;
    const numeric = code.replace('sh', '').replace('sz', '');
    if (numeric === '518880') {
        section.innerHTML = `
            <h2>📖 什么是黄金ETF？</h2>
            <div class="info-grid">
                <div class="info-item">
                    <h4>💰 黄金ETF是什么？</h4>
                    <p>黄金ETF(Exchange Traded Fund)是一种在交易所上市交易的开放式基金，以黄金为基础资产，追踪黄金价格波动。投资者可以像买卖股票一样交易黄金ETF。</p>
                </div>
                <div class="info-item">
                    <h4>📈 518880 华夏黄金ETF</h4>
                    <p>国内规模最大的黄金ETF之一，主要投资于上海黄金交易所的黄金现货合约，为投资者提供便捷的黄金投资渠道。</p>
                </div>
                <div class="info-item">
                    <h4>⚠️ 投资风险</h4>
                    <p>黄金ETF受金价波动影响，还包括市场风险、流动性风险等。本系统仅供参考，不构成投资建议，投资需谨慎。</p>
                </div>
            </div>
        `;
    } else {
        section.innerHTML = `
            <h2>📖 ${name || code} 技术分析简介</h2>
            <div class="info-grid">
                <div class="info-item">
                    <h4>📊 技术分析说明</h4>
                    <p>本系统通过移动平均线(MA)、MACD、KDJ、RSI、布林带等技术指标，对${name || code}的历史价格走势进行综合技术分析，为投资决策提供参考。</p>
                </div>
                <div class="info-item">
                    <h4>⚠️ 投资风险提示</h4>
                    <p>技术分析仅供参考，不构成投资建议。股票投资受多种因素影响，包括但不限于公司业绩、宏观经济环境、政策因素等。投资有风险，入市需谨慎。</p>
                </div>
            </div>
        `;
    }
}

function updateNewsTitle(code) {
    const numeric = code.replace('sh', '').replace('sz', '');
    const newsHeading = document.getElementById('newsSectionTitle');
    if (newsHeading) {
        newsHeading.textContent = numeric === '518880' ? '📰 黄金国际新闻' : '📰 相关新闻';
    }
}

function showLoading(show) {
    const el = document.getElementById('pageLoading');
    if (el) {
        if (show) el.classList.remove('hidden');
        else el.classList.add('hidden');
    }
}

// ========== 指标说明展示 ==========
function showIndicator(name) {
    document.querySelectorAll('.indicator-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.indicator-tab').forEach(el => el.classList.remove('active'));
    const contentEl = document.getElementById('ind-' + name);
    if (contentEl) contentEl.classList.add('active');
    if (event && event.target) event.target.classList.add('active');
}

// ========== 渲染：指标卡片 ==========
function renderSummary(data) {
    const latest = data.latest;
    if (!latest) return;
    const cards = [
        {
            label: '最新价',
            value: latest['收盘'].toFixed(3),
            change: latest['涨跌幅'],
            icon: latest['涨跌幅'] >= 0 ? '💹' : '💔'
        },
        {
            label: 'MA5 短期',
            value: latest['MA5'].toFixed(3),
            sub: latest['收盘'] > latest['MA5'] ? '价格>均线↑' : '价格<均线↓',
            icon: latest['收盘'] > latest['MA5'] ? '✅' : '⚠️'
        },
        {
            label: 'MA10 中期',
            value: latest['MA10'].toFixed(3),
            sub: latest['MA5'] > latest['MA10'] ? '多头排列' : '空头排列',
            icon: latest['MA5'] > latest['MA10'] ? '✅' : '⚠️'
        },
        {
            label: 'RSI',
            value: latest['RSI'].toFixed(1),
            sub: latest['RSI'] > 70 ? '超买⚠️' : latest['RSI'] < 30 ? '超卖📈' : '正常区间',
            icon: latest['RSI'] > 70 ? '⚠️' : latest['RSI'] < 30 ? '📈' : '➡️'
        },
        {
            label: 'KDJ J值',
            value: latest['J'].toFixed(1),
            sub: latest['J'] > 80 ? '超买⚠️' : latest['J'] < 20 ? '超卖📈' : '正常',
            icon: latest['J'] > 80 ? '⚠️' : latest['J'] < 20 ? '📈' : '➡️'
        },
        {
            label: '资金流向',
            value: (latest['累计净流入'] / 1e8).toFixed(2) + '亿',
            sub: latest['累计净流入'] > 0 ? '净流入↑' : '净流出↓',
            icon: latest['累计净流入'] > 0 ? '✅' : '⚠️'
        }
    ];

    document.getElementById('summaryCards').innerHTML = cards.map(c => `
        <div class="card">
            <h3>${c.icon} ${c.label}</h3>
            <div class="value">${c.value}</div>
            <div class="label">${c.sub || ''}</div>
            ${c.change !== undefined ? `<div class="change ${c.change >= 0 ? 'up' : 'down'}">${c.change >= 0 ? '+' : ''}${c.change.toFixed(2)}%</div>` : ''}
        </div>
    `).join('');
}

// ========== 渲染：分析信号 ==========
function renderSignals(data, maKey) {
    const signals = (data.signals || []).filter(s => s[0] !== '网格信号');
    const signalGrid = document.getElementById('signalGrid');
    signalGrid.innerHTML = signals.map(s => {
        const isBullish = s[1].includes('✅') || s[1].includes('📈');
        const isBearish = s[1].includes('⚠️') && !s[1].includes('谨慎');
        const cls = isBullish ? 'bullish' : isBearish ? 'neutral' : 'neutral';
        return `
            <div class="signal-item ${cls}">
                <span class="signal-icon">${s[1].split(' ')[0]}</span>
                <div class="signal-info">
                    <h4>${s[0]}</h4>
                    <div class="status">${s[1]}</div>
                    <div class="desc">${s[2]}</div>
                </div>
            </div>
        `;
    }).join('');

updateAdvice(data, maKey);
}

// ========== 渲染：综合分析建议 ==========
function updateAdvice(data, maKey) {
    const signals = data.signals || [];

    let bullishCount = 0, bearishCount = 0;
    signals.forEach(s => {
        if (s[1].includes('✅') || s[1].includes('📈')) bullishCount++;
        if (s[1].includes('⚠️') && !s[1].includes('谨慎')) bearishCount++;
    });

    const adviceEl = document.getElementById('finalAdvice');
    let tradeSignal = data.trade_signal || '观望';

    if (tradeSignal === '买入') {
        adviceEl.className = 'final-advice bullish';
        adviceEl.innerHTML = '<h3>📈 综合建议：短期偏多</h3><p>多个指标显示多方占优，但需注意KDJ超买风险。建议逢低布局，控制仓位，设定止损位。</p>';
    } else if (tradeSignal === '卖出') {
        adviceEl.className = 'final-advice bearish';
        adviceEl.innerHTML = '<h3>📉 综合建议：短期偏空</h3><p>多个指标显示空方占优，建议谨慎操作。可关注超卖信号出现时的反弹机会，但需快进快出。</p>';
    } else {
        adviceEl.className = 'final-advice neutral';
        adviceEl.innerHTML = '<h3>➡️ 综合建议：震荡整理</h3><p>多空信号交织，市场方向不明。建议观望为主，等待趋势明确后再操作。不要盲目追涨杀跌。</p>';
    }
}

// ========== 渲染：综合交易信号 ==========
function renderTradeSignal(data, maKey) {
    const bar = document.getElementById('tradeSignalBar');
    const valueEl = document.getElementById('tradeSignalValue');
    const detailEl = document.getElementById('tradeSignalDetail');
    if (!bar || !valueEl) return;

    const signal = data.trade_signal || '观望';
    const latest = data.latest || {};
    const gridSignals = data.grid_signals || {};
    const selectedMaKey = maKey || 'MA20';
    const grid = gridSignals[selectedMaKey] || data.grid_signal || {};
    const signals = data.signals || [];

    // 显示信号栏
    bar.style.display = 'flex';

    // 样式
    bar.className = 'trade-signal-bar';
    if (signal === '买入') {
        bar.classList.add('signal-buy');
        valueEl.className = 'signal-value buy';
        valueEl.textContent = '🟢 买入';
    } else if (signal === '卖出') {
        bar.classList.add('signal-sell');
        valueEl.className = 'signal-value sell';
        valueEl.textContent = '🔴 卖出';
    } else {
        bar.classList.add('signal-watch');
        valueEl.className = 'signal-value watch';
        valueEl.textContent = '➡️ 观望';
    }

    // 关键指标提示
    const rsi = latest.RSI || 0;
    const j = latest.J || 0;
    const macdHist = latest.MACD_HIST || 0;
    const parts = [];
    parts.push(`RSI: <span class="${rsi > 70 ? 'bad' : rsi < 30 ? 'ok' : 'warn'}">${rsi.toFixed(1)}</span>`);
    parts.push(`KDJ-J: <span class="${j > 80 ? 'bad' : j < 20 ? 'ok' : 'warn'}">${j.toFixed(1)}</span>`);
    parts.push(`MACD柱: <span class="${macdHist > 0 ? 'ok' : 'bad'}">${macdHist.toFixed(4)}</span>`);

    // 网格信息
    if (grid.close) {
        const gridEmoji = {'买入': '📈', '卖出': '📉', '持有': '➡️'}[grid.signal] || '➡️';
        parts.push(`${gridEmoji}网格${grid.current_grid}/${grid.total_grids}格`);
        parts.push(`📍持仓${Math.round(grid.position_ratio * 100)}%`);
    }

    detailEl.innerHTML = parts.join(' &nbsp;|&nbsp; ');
}

// ========== 渲染：网格交易专属卡片 ==========
function renderGridCard(data) {
    const card = document.getElementById('gridCard');
    if (!card) return;

    // 从 grid_signals 字典中取当前选中均线的结果
    const selectEl = document.getElementById('gridMaSelect');
    const maKey = selectEl ? selectEl.value.toUpperCase() : 'MA20';
    const gridSignals = data.grid_signals || {};
    const grid = gridSignals[maKey] || data.grid_signal || {};
    if (!grid || !grid.close) {
        card.style.display = 'none';
        return;
    }
    card.style.display = 'block';

    const n = grid.total_grids || 10;
    const cur = grid.current_grid || 0;
    const action = grid.signal || '持有';

    // 卡片颜色
    card.className = 'grid-card';
    if (action === '买入') card.classList.add('signal-buy');
    else if (action === '卖出') card.classList.add('signal-sell');
    else card.classList.add('signal-hold');

    // 动态/静态标签
    const badgeEl = document.getElementById('gridDynamicBadge');
    if (grid.dynamic_spread) {
        badgeEl.textContent = 'ATR动态';
        badgeEl.className = 'grid-dynamic-badge';
    } else {
        badgeEl.textContent = '固定参数';
        badgeEl.className = 'grid-dynamic-badge static';
    }

    // 参数区
    document.getElementById('gridPrice').textContent = grid.close?.toFixed(4) || '-';
    document.getElementById('gridSpread').textContent = `±${grid.grid_spread_pct?.toFixed(1)}%`;
    document.getElementById('gridStep').textContent = `${grid.step_pct?.toFixed(2)}%/格`;

    // ATR 显示
    const atrEl = document.getElementById('gridATR');
    if (grid.atr) {
        atrEl.textContent = `${grid.atr.toFixed(4)} (${grid.atr_pct?.toFixed(2)}%)`;
        atrEl.style.color = '#667eea';
    } else {
        atrEl.textContent = '无数据';
        atrEl.style.color = '#555';
    }

    // 均线偏离度
    const ma20DevEl = document.getElementById('gridMA20Dev');
    if (grid.ma_deviation_pct !== undefined && grid.ma_deviation_pct !== null) {
        const dev = grid.ma_deviation_pct;
        ma20DevEl.textContent = `${dev > 0 ? '+' : ''}${dev.toFixed(2)}%`;
        ma20DevEl.style.color = dev > 0 ? '#26a69a' : '#ef5350';
    } else {
        ma20DevEl.textContent = '-';
        ma20DevEl.style.color = '#555';
    }

    // MA20 基准价显示在顶部
    const titleEl = card.querySelector('.grid-card-title');
    if (titleEl) {
        const badgeEl = document.getElementById('gridDynamicBadge');
        const baseLabel = grid.base_label || `基准=${grid.base_price?.toFixed(4)}`;
        badgeEl.title = `基准价：${baseLabel}`;
    }

    const posPct = Math.round((grid.position_ratio || 0) * 100);
    const posEl = document.getElementById('gridPosition');
    posEl.textContent = `${posPct}%`;
    posEl.style.color = posPct >= 70 ? '#26a69a' : posPct >= 40 ? '#FF9800' : '#ef5350';

    // 网格可视化条
    const visualEl = document.getElementById('gridVisual');
    let barCells = '';
    for (let i = 0; i < n; i++) {
        const filled = i < cur ? 'filled' : '';
        const current = i === cur ? 'current' : '';
        barCells += `<div class="grid-bar-cell ${filled} ${current}"></div>`;
    }
    const pointerLeft = n > 0 ? ((cur + 0.5) / n * 100) : 50;
    visualEl.innerHTML = `
        <div class="grid-bar-wrapper">
            <div class="grid-bar-bg">${barCells}</div>
            <div class="grid-bar-pointer" style="left:${pointerLeft}%"></div>
        </div>
        <div class="grid-labels">
            <span>${grid.lower_bound?.toFixed(3)} (底)</span>
            <span>${grid.upper_bound?.toFixed(3)} (顶)</span>
        </div>
    `;

    // 底部建议
    const footerEl = document.getElementById('gridFooter');
    const emoji = {'买入': '📈', '卖出': '📉', '持有': '➡️'}[action] || '➡️';
    const cls = {'买入': 'action-buy', '卖出': 'action-sell', '持有': 'action-hold'}[action] || 'action-hold';
    footerEl.innerHTML = `${emoji} <span class="${cls}">${action}</span>：${grid.action_desc || ''} &nbsp;|&nbsp; 📍 第${cur}格/共${n}格`;
}

// ========== 均线切换重算网格 ==========
function onMaChange() {
    if (!_cachedData) return;
    const selectEl = document.getElementById('gridMaSelect');
    const maKey = selectEl ? selectEl.value.toUpperCase() : 'MA20';
    // 用缓存数据直接重算（grid_signals 已包含所有均线结果）
    renderGridCard(_cachedData);
    // 联动更新交易信号区域
    renderTradeSignal(_cachedData, maKey);
    // 联动更新综合建议
    updateAdvice(_cachedData, maKey);
}

async function loadNews(symbol) {
    try {
        const url = symbol ? `/api/news?symbol=${encodeURIComponent(symbol)}` : '/api/news';
        const resp = await fetch(url);
        const data = await resp.json();
        renderNews(data.news, symbol);
    } catch (e) {
        document.getElementById('newsGrid').innerHTML = '<div class="loading">新闻加载失败</div>';
    }
}

function getStockLabel(symbol) {
    const numeric = symbol.replace('sh', '').replace('sz', '');
    if (numeric === '518880') return '黄金ETF';
    return null; // use server-provided name
}

function renderNews(news, symbol) {
    const grid = document.getElementById('newsGrid');
    if (!news || news.length === 0) {
        grid.innerHTML = '<div class="loading">暂无新闻</div>';
        return;
    }
    grid.innerHTML = news.map(n => `
        <a href="${n.url}" target="_blank" class="news-item">
            <h4>${n.title}</h4>
            <div class="meta">
                <span class="source">${n.source}</span>
                <span class="time">${n.time}</span>
            </div>
        </a>
    `).join('');
}

// ========== 渲染：图表 ==========
function renderCharts(data) {
    const dates = data.dates || [];
    const kdata = data.kdata || [];

    // 保存到全局变量，供 tooltip 使用
    _chartDates = dates;
    _chartKdata = kdata;

    // 主图：K线图（蜡烛图）
    const mainChart = echarts.init(document.getElementById('mainChart'));
    // kdata 格式: [[开盘, 收盘, 最低, 最高], ...] → ECharts candlestick: [open, close, low, high]
    const candlestickData = kdata.map(d => [d[0], d[1], d[2], d[3]]);
    mainChart.setOption({
        backgroundColor: 'transparent',
        title: { text: '📈 K线图（蜡烛图）', textStyle: { color: '#fff', fontSize: 16 }, left: 0 },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            formatter: params => {
                if (!params || params.length === 0) return '';
                const dateStr = params[0].axisValue;
                // 通过日期在全局数组中查找对应索引
                const idx = _chartDates.indexOf(dateStr);
                if (idx === -1) return '未找到数据';
                const k = _chartKdata[idx];
                if (!k || k.length < 4) return '数据格式错误';
                // k 格式: [开盘, 收盘, 最低, 最高]
                const open = Number(k[0]), close = Number(k[1]), low = Number(k[2]), high = Number(k[3]);
                if (isNaN(open) || isNaN(close)) return '数据解析错误';
                const color = close >= open ? '#26a69a' : '#ef5350';
                return `日期: ${dateStr}<br>`
                    + `开盘: <span style="color:${color}">${open.toFixed(2)}</span><br>`
                    + `收盘: <span style="color:${color}">${close.toFixed(2)}</span><br>`
                    + `最低: ${low.toFixed(2)}<br>`
                    + `最高: ${high.toFixed(2)}`;
            }
        },
        legend: {
            data: ['K线', 'MA5', 'MA10', 'MA20', '布林上轨', '布林下轨'],
            top: 30,
            textStyle: { color: '#aaa' }
        },
        grid: { left: '8%', right: '8%', top: '25%', bottom: '15%' },
        xAxis: {
            type: 'category',
            data: dates,
            axisLine: { lineStyle: { color: '#444' } },
            axisLabel: { color: '#888' }
        },
        yAxis: {
            type: 'value',
            scale: true,
            axisLine: { lineStyle: { color: '#444' } },
            axisLabel: { color: '#888' },
            splitLine: { lineStyle: { color: '#333' } }
        },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', start: 0, end: 100 }
        ],
        series: [
            {
                name: 'K线',
                type: 'candlestick',
                data: candlestickData,
                itemStyle: {
                    color: '#26a69a',    // 上涨：绿色
                    color0: '#ef5350',   // 下跌：红色
                    borderColor: '#26a69a',
                    borderColor0: '#ef5350'
                }
            },
            {
                name: 'MA5',
                type: 'line',
                data: data.MA5,
                smooth: true,
                lineStyle: { width: 1, color: '#FF9800' },
                symbol: 'none'
            },
            {
                name: 'MA10',
                type: 'line',
                data: data.MA10,
                smooth: true,
                lineStyle: { width: 1, color: '#4CAF50' },
                symbol: 'none'
            },
            {
                name: 'MA20',
                type: 'line',
                data: data.MA20,
                smooth: true,
                lineStyle: { width: 1, color: '#9C27B0' },
                symbol: 'none'
            },
            {
                name: '布林上轨',
                type: 'line',
                data: data.BB_UPPER,
                smooth: true,
                lineStyle: { width: 1, color: '#666', type: 'dashed' },
                symbol: 'none'
            },
            {
                name: '布林下轨',
                type: 'line',
                data: data.BB_LOWER,
                smooth: true,
                lineStyle: { width: 1, color: '#666', type: 'dashed' },
                symbol: 'none'
            }
        ]
    });
    chartInstances.main = mainChart;

    // MACD
    const macdChart = echarts.init(document.getElementById('macdChart'));
    macdChart.setOption({
        backgroundColor: 'transparent',
        title: { text: '📉 MACD 趋势动量', textStyle: { color: '#fff', fontSize: 16 }, left: 0 },
        tooltip: { trigger: 'axis' },
        legend: { data: ['MACD', 'Signal', 'Histogram'], top: 30, textStyle: { color: '#aaa' } },
        grid: { left: '8%', right: '8%', top: '25%', bottom: '15%' },
        xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888' } },
        yAxis: { type: 'value', axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#333' } } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: [
            { name: 'MACD', type: 'line', data: data.MACD, smooth: true, lineStyle: { width: 1, color: '#2196F3' } },
            { name: 'Signal', type: 'line', data: data.MACD_SIGNAL, smooth: true, lineStyle: { width: 1, color: '#FF9800' } },
            { name: 'Histogram', type: 'bar', data: data.MACD_HIST.map(v => ({ value: v, itemStyle: { color: v >= 0 ? '#26a69a' : '#ef5350' } })) }
        ]
    });
    chartInstances.macd = macdChart;

    // KDJ
    const kdjChart = echarts.init(document.getElementById('kdjChart'));
    kdjChart.setOption({
        backgroundColor: 'transparent',
        title: { text: '📊 KDJ 随机指标', textStyle: { color: '#fff', fontSize: 16 }, left: 0 },
        tooltip: { trigger: 'axis' },
        legend: { data: ['K', 'D', 'J'], top: 30, textStyle: { color: '#aaa' } },
        grid: { left: '8%', right: '8%', top: '25%', bottom: '15%' },
        xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888' } },
        yAxis: { type: 'value', min: 0, max: 100, axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#333' } } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: [
            { name: 'K', type: 'line', data: data.K, smooth: true, lineStyle: { width: 1, color: '#2196F3' } },
            { name: 'D', type: 'line', data: data.D, smooth: true, lineStyle: { width: 1, color: '#FF9800' } },
            { name: 'J', type: 'line', data: data.J, smooth: true, lineStyle: { width: 1, color: '#9C27B0' } },
            { name: '超买线', type: 'line', data: Array(dates.length).fill(80), smooth: true, lineStyle: { width: 1, color: '#ef5350', type: 'dashed' } },
            { name: '超卖线', type: 'line', data: Array(dates.length).fill(20), smooth: true, lineStyle: { width: 1, color: '#26a69a', type: 'dashed' } }
        ]
    });
    chartInstances.kdj = kdjChart;

    // 成交量
    const volumeChart = echarts.init(document.getElementById('volumeChart'));
    const volColors = kdata.map(d => d[1] >= d[0] ? '#26a69a' : '#ef5350');
    volumeChart.setOption({
        backgroundColor: 'transparent',
        title: { text: '📦 成交量分析', textStyle: { color: '#fff', fontSize: 16 }, left: 0 },
        tooltip: { trigger: 'axis' },
        grid: { left: '8%', right: '8%', top: '25%', bottom: '15%' },
        xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888' } },
        yAxis: { type: 'value', axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888', formatter: v => (v/1e6).toFixed(0) + 'M' }, splitLine: { lineStyle: { color: '#333' } } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: [{ type: 'bar', data: data.volume.map((v, i) => ({ value: v, itemStyle: { color: volColors[i] } })) }]
    });
    chartInstances.volume = volumeChart;

    // 资金流向
    const moneyChart = echarts.init(document.getElementById('moneyChart'));
    const flowColors = (data.资金净流入 || []).map(v => v >= 0 ? '#26a69a' : '#ef5350');
    moneyChart.setOption({
        backgroundColor: 'transparent',
        title: { text: '💰 资金流向', textStyle: { color: '#fff', fontSize: 16 }, left: 0 },
        tooltip: { trigger: 'axis' },
        legend: { data: ['每日净流入', '累计净流入'], top: 30, textStyle: { color: '#aaa' } },
        grid: { left: '8%', right: '8%', top: '25%', bottom: '15%' },
        xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888' } },
        yAxis: { type: 'value', axisLine: { lineStyle: { color: '#444' } }, axisLabel: { color: '#888', formatter: v => (v/1e6).toFixed(0) + 'M' }, splitLine: { lineStyle: { color: '#333' } } },
        dataZoom: [{ type: 'inside', start: 0, end: 100 }],
        series: [
            { name: '每日净流入', type: 'bar', data: (data.资金净流入 || []).map((v, i) => ({ value: v, itemStyle: { color: flowColors[i] } })) },
            { name: '累计净流入', type: 'line', data: data.累计净流入 || [], smooth: true, lineStyle: { width: 2, color: '#9C27B0' } }
        ]
    });
    chartInstances.money = moneyChart;

    // 响应式
    window.addEventListener('resize', () => {
        Object.values(chartInstances).forEach(chart => chart.resize());
    });
}

// ========== 模拟交易 ==========
async function runSimulation() {
    const simCard = document.getElementById('simulationCard');
    const simLoading = document.getElementById('simLoading');
    const simResults = document.getElementById('simResults');

    if (!simCard) return;

    // 显示卡片（默认隐藏）
    simCard.style.display = 'block';

    // 获取参数
    const capital = parseFloat(document.getElementById('simCapital').value) || 100000;
    const gridCount = parseInt(document.getElementById('simGridCount').value) || 10;
    const spreadType = document.getElementById('simSpreadType').value || 'fixed';
    const maKey = document.getElementById('simMaKey').value || 'MA20';

    // 获取当前页面的日期范围
    const startInput = document.getElementById('startDateInput');
    const endInput = document.getElementById('endDateInput');
    const startDate = startInput ? startInput.value : null;
    const endDate = endInput ? endInput.value : null;

    // 显示加载
    simLoading.style.display = 'flex';
    simResults.style.display = 'none';

    try {
        const resp = await fetch('/api/backtest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: currentSymbol,
                start_date: startDate,
                end_date: endDate,
                initial_capital: capital,
                grid_count: gridCount,
                spread_type: spreadType,
                base_ma_key: maKey,
            })
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ error: '回测失败' }));
            throw new Error(err.error || `HTTP ${resp.status}`);
        }

        const result = await resp.json();

        // 渲染结果
        renderSimulationResults(result);

        // 先显示结果区域，等浏览器计算完容器尺寸后再渲染图表
        simResults.style.display = 'block';
        setTimeout(() => {
            renderEquityCurve(result);
            renderGridMarkersOnChart(result);
        }, 150);

    } catch (e) {
        console.error('回测失败:', e);
        simResults.innerHTML = `<div style="color:#ef5350;padding:20px;">回测失败: ${e.message}</div>`;
        simResults.style.display = 'block';
    } finally {
        simLoading.style.display = 'none';
    }
}

function renderSimulationResults(data) {
    const kpisEl = document.getElementById('simKpis');
    if (!kpisEl) return;

    const isProfit = data.total_return_pct >= 0;
    const sign = isProfit ? '+' : '';

    const kpis = [
        { label: '总收益率', value: `${sign}${data.total_return_pct}%`, cls: isProfit ? 'positive' : 'negative' },
        { label: '最终资金', value: `${(data.final_equity / 10000).toFixed(2)}万`, cls: isProfit ? 'positive' : 'negative' },
        { label: '交易次数', value: data.num_trades, cls: '' },
        { label: '胜率', value: `${data.win_rate}%`, cls: data.win_rate >= 50 ? 'positive' : 'negative' },
        { label: '最大回撤', value: `${data.max_drawdown_pct}%`, cls: data.max_drawdown_pct > 10 ? 'negative' : '' },
    ];

    kpisEl.innerHTML = kpis.map(k => `
        <div class="sim-kpi-card">
            <div class="kpi-label">${k.label}</div>
            <div class="kpi-value ${k.cls}">${k.value}</div>
        </div>
    `).join('');

    // 渲染交易记录表格
    const tbody = document.getElementById('simTradeTableBody');
    if (!tbody) return;

    if (!data.trade_history || data.trade_history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="color:#888;text-align:center;">暂无交易记录</td></tr>';
        return;
    }

    tbody.innerHTML = data.trade_history.map((t, i) => {
        const pnlCls = t.pnl >= 0 ? 'positive' : 'negative';
        const pnlSign = t.pnl >= 0 ? '+' : '';
        return `
            <tr>
                <td>${i + 1}</td>
                <td>${t.entry_date}</td>
                <td>${t.entry_price.toFixed(3)}</td>
                <td>第${t.entry_grid}格</td>
                <td>${t.exit_date}</td>
                <td>${t.exit_price.toFixed(3)}</td>
                <td class="${pnlCls}">${pnlSign}${t.pnl.toFixed(2)}</td>
                <td class="${pnlCls}">${pnlSign}${t.pnl_pct.toFixed(2)}%</td>
            </tr>
        `;
    }).join('');
}

function renderEquityCurve(data) {
    const chartEl = document.getElementById('simEquityChart');
    if (!chartEl) return;

    // 销毁旧图表
    if (chartInstances.simEquity) {
        chartInstances.simEquity.dispose();
    }

    const chart = echarts.init(chartEl);
    const equityData = (data.equity_curve || []).map(p => [p.date, p.equity]);

    chart.setOption({
        backgroundColor: 'transparent',
        title: {
            text: '权益曲线',
            textStyle: { color: '#fff', fontSize: 14 },
            left: 0,
            top: 5
        },
        tooltip: {
            trigger: 'axis',
            formatter: params => {
                if (!params || params.length === 0) return '';
                const p = params[0];
                return `${p.value[0]}<br/>权益: <b>${(p.value[1] / 10000).toFixed(2)}万</b>元`;
            }
        },
        grid: { left: '10%', right: '5%', top: '25%', bottom: '12%' },
        xAxis: {
            type: 'category',
            data: (data.equity_curve || []).map(p => p.date),
            axisLabel: { color: '#888', fontSize: 10, interval: Math.floor((data.equity_curve || []).length / 6) },
            axisLine: { lineStyle: { color: '#444' } }
        },
        yAxis: {
            type: 'value',
            axisLabel: {
                color: '#888',
                formatter: v => (v / 10000).toFixed(1) + '万'
            },
            splitLine: { lineStyle: { color: '#333' } },
            axisLine: { lineStyle: { color: '#444' } }
        },
        dataZoom: [
            { type: 'inside', start: 0, end: 100 },
            { type: 'slider', start: 0, end: 100, height: 20, bottom: 0 }
        ],
        series: [{
            name: '权益',
            type: 'line',
            data: equityData,
            smooth: true,
            lineStyle: { width: 2, color: '#667eea' },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(102,126,234,0.3)' },
                        { offset: 1, color: 'rgba(102,126,234,0)' }
                    ]
                }
            },
            symbol: 'none'
        }]
    });

    chartInstances.simEquity = chart;
}

function renderGridMarkersOnChart(data) {
    const mainChart = chartInstances.main;
    if (!mainChart || !data.trade_history || data.trade_history.length === 0) return;

    const buyMarkers = data.trade_history.map(t => ({
        name: '买入',
        coord: [t.entry_date, t.entry_price],
        value: t.entry_price,
        itemStyle: { color: '#26a69a' }
    }));

    const sellMarkers = data.trade_history.map(t => ({
        name: '卖出',
        coord: [t.exit_date, t.exit_price],
        value: t.exit_price,
        itemStyle: { color: '#ef5350' }
    }));

    // 获取当前 option 并追加 series
    const currentOption = mainChart.getOption();
    const existingSeries = currentOption.series || [];

    // 过滤掉旧的买卖点系列
    const filteredSeries = existingSeries.filter(s =>
        s.name !== '买入点' && s.name !== '卖出点'
    );

    mainChart.setOption({
        series: [
            ...filteredSeries,
            {
                name: '买入点',
                type: 'scatter',
                symbol: 'triangle',
                symbolSize: 10,
                data: buyMarkers,
                itemStyle: { color: '#26a69a' },
                tooltip: {
                    formatter: p => `买入<br/>日期: ${p.data.coord[0]}<br/>价格: ${p.data.coord[1].toFixed(3)}`
                }
            },
            {
                name: '卖出点',
                type: 'scatter',
                symbol: 'triangle',
                symbolSize: 10,
                data: sellMarkers,
                itemStyle: { color: '#ef5350' },
                tooltip: {
                    formatter: p => `卖出<br/>日期: ${p.data.coord[0]}<br/>价格: ${p.data.coord[1].toFixed(3)}`
                }
            }
        ]
    });
}

// ========== 启动 ==========
document.addEventListener('DOMContentLoaded', () => {
    // 启动实时时钟
    updateClock();
    setInterval(updateClock, 1000);

    // 初始化图表实例
    chartInstances = {};

    // 显示模拟交易卡片
    const simCard = document.getElementById('simulationCard');
    if (simCard) simCard.style.display = 'block';

    // 加载用户状态
    loadUserStatus();

    // 从 URL 读取初始参数，无则使用默认值
    const params = new URLSearchParams(window.location.search);
    const symbol    = params.get('symbol')    || 'sh518880';
    const startDate = params.get('start_date') || null;
    const endDate   = params.get('end_date')   || null;

    // 填充表单
    const codeInput   = document.getElementById('stockCodeInput');
    const startInput  = document.getElementById('startDateInput');
    const endInput    = document.getElementById('endDateInput');
    if (codeInput)  codeInput.value  = symbol;
    if (startInput) startInput.value = startDate || '';
    if (endInput)   endInput.value   = endDate   || '';

    // 设置默认近3月快捷按钮高亮（仅在没有指定日期时）
    if (!startDate && !endDate) {
        highlightQuickBtn(3);
        // 实际加载用近90天（3个月≈90天）
        const end   = new Date();
        const start = new Date();
        start.setDate(start.getDate() - 90);
        if (startInput) startInput.value = fmtDate(start);
        if (endInput)   endInput.value   = fmtDate(end);
    }

    // 加载数据和新闻
    loadStockData(symbol, startDate || (startInput ? startInput.value : null),
                          endDate   || (endInput   ? endInput.value   : null));
    loadNews(symbol);

    // 每5分钟刷新新闻（使用当前股票代码）
    setInterval(() => loadNews(currentSymbol), 5 * 60 * 1000);
});
