<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { storeToRefs } from 'pinia'
import { normalizeSymbol } from '@/utils/symbol'

const simStore = useSimulationStore()
const { autoTradeTasks, taskCount, runningTaskCount, isAutoTrading, realtimePrices } = storeToRefs(simStore)

// Add task form
const showAddForm = ref(false)
const addForm = ref({
  symbol: '',
  grid_count: 10,
  base_ma_key: 'MA20',
  grid_spread: 0.10,
  position_size: 1.0,
  check_interval: 30,
  allocated_funds: 30000,
})
const addError = ref<string | null>(null)

// Edit task form
const editingSymbol = ref<string | null>(null)
const editForm = ref({
  grid_count: 10,
  base_ma_key: 'MA20',
  grid_spread: 0.10,
  position_size: 1.0,
  check_interval: 30,
  allocated_funds: 30000,
})

const gridCountOptions = [5, 10, 15, 20]
const maKeyOptions = ['MA5', 'MA10', 'MA20', 'MA60']

function signalColor(signal: string | null) {
  if (!signal) return '#7986cb'
  if (signal === '买入') return '#ef5350'
  if (signal === '卖出') return '#26a69a'
  if (signal === '持有') return '#ff9800'
  return '#7986cb'
}

function signalBg(signal: string | null) {
  if (!signal) return 'rgba(121,134,203,0.1)'
  if (signal === '买入') return 'rgba(239,83,80,0.1)'
  if (signal === '卖出') return 'rgba(38,166,154,0.1)'
  if (signal === '持有') return 'rgba(255,152,0,0.1)'
  return 'rgba(121,134,203,0.1)'
}

function openAddForm() {
  addForm.value = { symbol: '', grid_count: 10, base_ma_key: 'MA20', grid_spread: 0.10, position_size: 1.0, check_interval: 30, allocated_funds: 30000 }
  addError.value = null
  showAddForm.value = true
}

async function handleAddTask() {
  const symbol = normalizeSymbol(addForm.value.symbol.trim() || 'sh518880').toLowerCase()
  if (!symbol) {
    addError.value = '请输入证券代码'
    return
  }
  addError.value = null
  const result = await simStore.addAutoTradeTask(symbol, addForm.value)
  if (result.success) {
    showAddForm.value = false
    await simStore.fetchAutoTradeTasks()
  } else {
    addError.value = result.error || '添加失败'
  }
}

function openEditForm(symbol: string) {
  const task = autoTradeTasks.value[symbol]
  if (!task) return
  editingSymbol.value = symbol
  editForm.value = {
    grid_count: task.task.grid_count ?? 10,
    base_ma_key: task.task.base_ma_key ?? 'MA20',
    grid_spread: task.task.grid_spread ?? 0.10,
    position_size: task.task.position_size ?? 1.0,
    check_interval: task.task.check_interval ?? 30,
    allocated_funds: task.task.allocated_funds ?? 30000,
  }
}

async function handleSaveEdit() {
  if (!editingSymbol.value) return
  await simStore.updateAutoTradeTask(editingSymbol.value, editForm.value)
  editingSymbol.value = null
  await simStore.fetchAutoTradeTasks()
}

async function handleDeleteTask(symbol: string) {
  const task = autoTradeTasks.value[symbol]
  if (task?.running) {
    await simStore.stopAutoTradeTask(symbol)
  }
  await simStore.deleteAutoTradeTask(symbol)
  await simStore.fetchAutoTradeTasks()
}

async function handleStartTask(symbol: string) {
  await simStore.startAutoTradeTask(symbol)
  await simStore.fetchAutoTradeTasks()
}

async function handleStopTask(symbol: string) {
  await simStore.stopAutoTradeTask(symbol)
  await simStore.fetchAutoTradeTasks()
}

async function handleStartAll() {
  await simStore.startAllAutoTradeTasks()
  await simStore.fetchAutoTradeTasks()
}

async function handleStopAll() {
  await simStore.stopAllAutoTradeTasks()
  await simStore.fetchAutoTradeTasks()
}

const taskList = computed(() => Object.values(autoTradeTasks.value))

function getRealtimePrice(symbol: string) {
  const rt = realtimePrices.value[symbol]
  return rt ? rt.price : null
}

function getPriceChange(symbol: string) {
  const rt = realtimePrices.value[symbol]
  if (!rt) return null
  const task = autoTradeTasks.value[symbol]
  const sig = task?.signal
  if (!sig?.close) return null
  const change = ((rt.price - sig.close) / sig.close * 100)
  return change
}
</script>

<template>
  <div class="auto-trade-panel">
    <div class="panel-header">
      <h3 class="panel-title">自动交易任务</h3>
      <div class="header-actions">
        <span class="task-summary">
          <span class="running-dot" :class="{ active: runningTaskCount > 0 }"></span>
          {{ runningTaskCount }} / {{ taskCount }} 运行中
        </span>
        <button class="btn-sm stop-all-btn" :disabled="isAutoTrading || runningTaskCount === 0" @click="handleStopAll">
          全部停止
        </button>
        <button class="btn-sm start-all-btn" :disabled="isAutoTrading || taskCount === 0" @click="handleStartAll">
          全部启动
        </button>
        <button class="btn-sm add-btn" :disabled="isAutoTrading" @click="openAddForm">
          + 添加任务
        </button>
      </div>
    </div>

    <!-- Add Task Form -->
    <div v-if="showAddForm" class="add-form">
      <h4 class="form-title">添加自动交易任务</h4>
      <div class="form-grid">
        <div class="form-item">
          <label>证券代码</label>
          <input v-model="addForm.symbol" type="text" class="input" placeholder="如 518880" />
        </div>
        <div class="form-item">
          <label>基准均线</label>
          <select v-model="addForm.base_ma_key" class="input select">
            <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
          </select>
        </div>
        <div class="form-item">
          <label>网格格数</label>
          <select v-model="addForm.grid_count" class="input select">
            <option v-for="n in gridCountOptions" :key="n" :value="n">{{ n }}格</option>
          </select>
        </div>
        <div class="form-item">
          <label>网格幅度</label>
          <input v-model.number="addForm.grid_spread" type="number" min="0.01" max="0.50" step="0.01" class="input" />
        </div>
        <div class="form-item">
          <label>每次仓位</label>
          <input v-model.number="addForm.position_size" type="number" min="0.1" max="1.0" step="0.1" class="input" />
        </div>
        <div class="form-item">
          <label>检查间隔</label>
          <input v-model.number="addForm.check_interval" type="number" min="10" max="300" step="10" class="input" />
          <span class="unit">秒</span>
        </div>
        <div class="form-item">
          <label>分配资金</label>
          <input v-model.number="addForm.allocated_funds" type="number" min="1000" step="10000" class="input" />
          <span class="unit">元</span>
        </div>
      </div>
      <div v-if="addError" class="error-msg">{{ addError }}</div>
      <div class="form-btns">
        <button class="btn-sm cancel-btn" @click="showAddForm = false">取消</button>
        <button class="btn-sm confirm-btn" :disabled="isAutoTrading" @click="handleAddTask">确认添加</button>
      </div>
    </div>

    <!-- Edit Task Form -->
    <div v-if="editingSymbol" class="add-form">
      <h4 class="form-title">编辑任务 · {{ editingSymbol }}</h4>
      <div class="form-grid">
        <div class="form-item">
          <label>基准均线</label>
          <select v-model="editForm.base_ma_key" class="input select">
            <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
          </select>
        </div>
        <div class="form-item">
          <label>网格格数</label>
          <select v-model="editForm.grid_count" class="input select">
            <option v-for="n in gridCountOptions" :key="n" :value="n">{{ n }}格</option>
          </select>
        </div>
        <div class="form-item">
          <label>网格幅度</label>
          <input v-model.number="editForm.grid_spread" type="number" min="0.01" max="0.50" step="0.01" class="input" />
        </div>
        <div class="form-item">
          <label>每次仓位</label>
          <input v-model.number="editForm.position_size" type="number" min="0.1" max="1.0" step="0.1" class="input" />
        </div>
        <div class="form-item">
          <label>检查间隔</label>
          <input v-model.number="editForm.check_interval" type="number" min="10" max="300" step="10" class="input" />
          <span class="unit">秒</span>
        </div>
        <div class="form-item">
          <label>分配资金</label>
          <input v-model.number="editForm.allocated_funds" type="number" min="1000" step="10000" class="input" />
          <span class="unit">元</span>
        </div>
      </div>
      <div class="form-btns">
        <button class="btn-sm cancel-btn" @click="editingSymbol = null">取消</button>
        <button class="btn-sm confirm-btn" :disabled="isAutoTrading" @click="handleSaveEdit">保存</button>
      </div>
    </div>

    <!-- Task Cards -->
    <div v-if="taskList.length === 0 && !showAddForm" class="empty-state">
      暂无自动交易任务，点击"添加任务"创建一个
    </div>

    <div v-else class="task-cards">
      <div v-for="ts in taskList" :key="ts.symbol" class="task-card">
        <div class="task-card-header">
          <div class="task-symbol-row">
            <span class="running-indicator" :class="{ running: ts.running }"></span>
            <div class="task-symbol-info">
              <span class="task-symbol">{{ ts.symbol.toUpperCase() }}</span>
              <span class="task-name">{{ ts.task_name || ts.symbol }}</span>
            </div>
            <span class="task-strategy">{{ ts.task.strategy === 'grid' ? '网格' : ts.task.strategy }}</span>
          </div>
          <div class="task-header-right">
            <div class="task-price" v-if="getRealtimePrice(ts.symbol) !== null">
              <span class="price-value">{{ getRealtimePrice(ts.symbol)?.toFixed(3) }}</span>
              <span
                class="price-change"
                :style="{ color: (getPriceChange(ts.symbol) ?? 0) >= 0 ? '#ef5350' : '#26a69a' }"
              >
                {{ (getPriceChange(ts.symbol) ?? 0) >= 0 ? '+' : '' }}{{ (getPriceChange(ts.symbol) ?? 0).toFixed(2) }}%
              </span>
            </div>
            <div class="task-signal" :style="{ color: signalColor(ts.signal?.signal ?? null) }">
              {{ ts.signal?.signal || '--' }}
            </div>
          </div>
        </div>

        <div class="task-card-body">
          <div class="task-params">
            <div class="param-item">
              <span class="param-label">基准均线</span>
              <span class="param-value">{{ ts.task.base_ma_key }}</span>
            </div>
            <div class="param-item">
              <span class="param-label">网格格数</span>
              <span class="param-value">{{ ts.task.grid_count }}格</span>
            </div>
            <div class="param-item">
              <span class="param-label">网格幅度</span>
              <span class="param-value">{{ (ts.task.grid_spread * 100).toFixed(1) }}%</span>
            </div>
            <div class="param-item">
              <span class="param-label">检查间隔</span>
              <span class="param-value">{{ ts.task.check_interval }}秒</span>
            </div>
            <div class="param-item">
              <span class="param-label">分配资金</span>
              <span class="param-value">{{ (ts.task.allocated_funds / 10000).toFixed(1) }}万</span>
            </div>
            <div class="param-item">
              <span class="param-label">剩余可用</span>
              <span class="param-value" :style="{ color: (ts.task_cash ?? 0) < 1000 ? '#ef5350' : '#26a69a' }">
                {{ ((ts.task_cash ?? ts.task.allocated_funds) / 10000).toFixed(1) }}万
              </span>
            </div>
            <div class="param-item">
              <span class="param-label">持仓/成本</span>
              <span class="param-value">{{ ts.task_position?.shares ?? 0 }}股 / {{ ts.task_position?.avg_cost?.toFixed(4) ?? '--' }}</span>
            </div>
            <div class="param-item">
              <span class="param-label">已实现盈亏</span>
              <span class="param-value" :style="{ color: (ts.task_pnl ?? 0) >= 0 ? '#ef5350' : '#26a69a' }">
                {{ (ts.task_pnl ?? 0) >= 0 ? '+' : '' }}{{ (ts.task_pnl ?? 0).toFixed(2) }}元
              </span>
            </div>
            <div class="param-item">
              <span class="param-label">浮动盈亏</span>
              <span class="param-value" :style="{ color: (ts.unrealized_pnl ?? 0) >= 0 ? '#ef5350' : '#26a69a' }">
                {{ (ts.unrealized_pnl ?? 0) >= 0 ? '+' : '' }}{{ (ts.unrealized_pnl ?? 0).toFixed(2) }}元
              </span>
            </div>
          </div>

          <div v-if="ts.signal" class="task-signal-detail" :style="{ background: signalBg(ts.signal.signal) }">
            <span>{{ ts.signal.action_desc || ts.signal.signal_text }}</span>
            <span class="signal-ratio">建议 {{ Math.round((ts.signal.position_ratio || 0) * 100) }}%</span>
          </div>

          <div class="task-last-check">
            上次检查: {{ ts.task.last_check || '--' }}
          </div>
        </div>

        <div class="task-card-actions">
          <template v-if="!ts.running">
            <button class="btn-sm edit-btn" :disabled="isAutoTrading" @click="openEditForm(ts.symbol)">编辑</button>
            <button class="btn-sm start-btn" :disabled="isAutoTrading" @click="handleStartTask(ts.symbol)">启动</button>
            <button class="btn-sm delete-btn" :disabled="isAutoTrading" @click="handleDeleteTask(ts.symbol)">删除</button>
          </template>
          <template v-else>
            <button class="btn-sm stop-btn" :disabled="isAutoTrading" @click="handleStopTask(ts.symbol)">停止</button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.auto-trade-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.panel-title {
  color: #7986cb;
  font-size: 15px;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  margin-right: 4px;
}

.running-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7986cb;
  &.active { background: #26a69a; }
}

.btn-sm {
  padding: 5px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover:not(:disabled) { opacity: 0.85; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.start-all-btn {
  background: linear-gradient(135deg, #26a69a, #00695c);
  color: white;
}

.stop-all-btn {
  background: rgba(239, 83, 80, 0.1);
  border: 1px solid #ef5350;
  color: #ef5350;
}

.add-btn {
  background: rgba(0, 242, 255, 0.1);
  border: 1px solid var(--accent-cyan);
  color: var(--accent-cyan);
}

.add-form {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.form-title {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 0 0 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 10px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;

  label {
    color: var(--text-muted);
    font-size: 11px;
  }
}

.input {
  padding: 6px 10px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;

  &:focus {
    outline: none;
    border-color: var(--accent-cyan);
  }
}

.select {
  cursor: pointer;
}

.unit {
  color: var(--text-muted);
  font-size: 11px;
  margin-top: 2px;
}

.error-msg {
  color: #ef5350;
  font-size: 12px;
  margin-bottom: 8px;
}

.form-btns {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.cancel-btn {
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.confirm-btn {
  background: linear-gradient(135deg, var(--accent-cyan), #00838f);
  color: white;
}

.empty-state {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 24px 0;
}

.task-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.task-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-symbol-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.task-symbol-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.task-symbol {
  font-size: 15px;
  font-weight: bold;
  color: var(--text-primary);
}

.task-name {
  font-size: 11px;
  color: var(--text-muted);
}

.running-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7986cb;
  flex-shrink: 0;
  &.running { background: #26a69a; box-shadow: 0 0 4px #26a69a; }
}

.task-strategy {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-hover);
  padding: 2px 6px;
  border-radius: 4px;
}

.task-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.task-price {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.price-value {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-primary);
  font-family: monospace;
}

.price-change {
  font-size: 12px;
  font-weight: bold;
}

.task-signal {
  font-size: 16px;
  font-weight: bold;
}

.task-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-params {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.param-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.param-label {
  color: var(--text-muted);
}

.param-value {
  color: var(--text-primary);
  font-family: monospace;
}

.task-signal-detail {
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  justify-content: space-between;
}

.signal-ratio {
  color: var(--accent-cyan);
}

.task-last-check {
  font-size: 11px;
  color: var(--text-muted);
}

.task-card-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.edit-btn {
  background: rgba(0, 242, 255, 0.1);
  border: 1px solid var(--accent-cyan);
  color: var(--accent-cyan);
}

.start-btn {
  background: linear-gradient(135deg, #26a69a, #00695c);
  color: white;
  flex: 1;
}

.delete-btn {
  background: rgba(239, 83, 80, 0.1);
  border: 1px solid #ef5350;
  color: #ef5350;
}

.stop-btn {
  background: linear-gradient(135deg, #ef5350, #c62828);
  color: white;
  flex: 1;
}
</style>