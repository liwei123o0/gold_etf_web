<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { storeToRefs } from 'pinia'
import { normalizeSymbol, formatSymbolForDisplay, stripPrefix } from '@/utils/symbol'

const simStore = useSimulationStore()
const { autoTradeTasks, taskCount, runningTaskCount, isAutoTrading, realtimePrices } = storeToRefs(simStore)

const ORDER_STORAGE_KEY = 'autotask_card_order'

function loadSavedOrder(): number[] {
  try {
    const raw = localStorage.getItem(ORDER_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveOrder(order: number[]) {
  localStorage.setItem(ORDER_STORAGE_KEY, JSON.stringify(order))
}

const draggedId = ref<number | null>(null)
const dragOverId = ref<number | null>(null)

const taskList = computed(() => {
  const tasks = Object.values(autoTradeTasks.value)
  const saved = loadSavedOrder()
  const validIds = new Set(tasks.map(t => t.id))
  const order = saved.filter(id => validIds.has(id))
  tasks.forEach(t => {
    if (!order.includes(t.id)) order.push(t.id)
  })
  return order.map(id => autoTradeTasks.value[id]).filter(Boolean)
})

watch(taskCount, (newCount) => {
  if (newCount === 0) {
    saveOrder([])
  }
})

function onDragStart(e: DragEvent, taskId: number) {
  draggedId.value = taskId
  e.dataTransfer!.effectAllowed = 'move'
  e.dataTransfer!.setData('text/plain', String(taskId))
  nextTick(() => {
    const el = (e.target as HTMLElement)?.closest('.task-card')
    if (el) el.classList.add('dragging')
  })
}

function onDragEnd(e: DragEvent) {
  draggedId.value = null
  dragOverId.value = null
  const el = (e.target as HTMLElement)?.closest('.task-card')
  if (el) el.classList.remove('dragging')
}

function onDragOver(e: DragEvent, taskId: number) {
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'move'
  if (draggedId.value !== null && draggedId.value !== taskId) {
    dragOverId.value = taskId
  }
}

function onDragLeave() {
  dragOverId.value = null
}

function onDrop(e: DragEvent, targetId: number) {
  e.preventDefault()
  dragOverId.value = null
  if (draggedId.value === null || draggedId.value === targetId) return
  const current = taskList.value.map(t => t.id)
  const fromIdx = current.indexOf(draggedId.value)
  const toIdx = current.indexOf(targetId)
  if (fromIdx === -1 || toIdx === -1) return
  const newOrder = [...current]
  newOrder.splice(fromIdx, 1)
  newOrder.splice(toIdx, 0, draggedId.value)
  saveOrder(newOrder)
}

function onContainerDrop(e: DragEvent) {
  if (!draggedId.value) return
  e.preventDefault()
  const cards = taskList.value
  let targetId = cards[cards.length - 1]?.id
  for (let i = 0; i < cards.length; i++) {
    const el = document.querySelector(`[data-task-id="${cards[i].id}"]`) as HTMLElement | null
    if (el) {
      const elRect = el.getBoundingClientRect()
      if (e.clientY < elRect.top + elRect.height / 2) {
        targetId = cards[i].id
        break
      }
    }
  }
  onDrop(e, targetId!)
}

// Add task form
const showAddForm = ref(false)
const addForm = ref({
  symbol: '',
  strategy: 'grid',
  grid_count: 10,
  base_ma_key: 'MA20',
  grid_spread: 0.10,
  position_size: 1.0,
  check_interval: 30,
  allocated_funds: 30000,
  stop_loss_pct: -5.0,
  take_profit_pct: 10.0,
  trend_ma_key: '',
  dynamic_interval: false,
  max_drawdown_pct: -15.0,
  position_shares: 0,
  position_avg_cost: 0,
})
const addError = ref<string | null>(null)

// Edit task form
const editingTaskId = ref<number | null>(null)
const editForm = ref({
  strategy: 'grid',
  grid_count: 10,
  base_ma_key: 'MA20',
  grid_spread: 0.10,
  position_size: 1.0,
  check_interval: 30,
  allocated_funds: 30000,
  stop_loss_pct: -5.0,
  take_profit_pct: 10.0,
  trend_ma_key: '',
  dynamic_interval: false,
  max_drawdown_pct: -15.0,
  position_shares: 0,
  position_avg_cost: 0,
})

const gridCountOptions = [5, 10, 15, 20]
const maKeyOptions = ['MA5', 'MA10', 'MA20', 'MA60']
const strategyOptions = [
  { value: 'grid', label: '网格交易' },
  { value: 'ma_trend', label: 'MA趋势跟踪' },
  { value: 'bollinger', label: '布林带均值回归' },
  { value: 'rsi', label: 'RSI超买超卖' },
  { value: 'macd_cross', label: 'MACD金叉死叉' },
]

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

const isGridStrategy = computed(() => addForm.value.strategy === 'grid')
const isBollingerStrategy = computed(() => addForm.value.strategy === 'bollinger')
const isRSIStrategy = computed(() => addForm.value.strategy === 'rsi')
const isMACDCrossStrategy = computed(() => addForm.value.strategy === 'macd_cross')

function openAddForm() {
  addForm.value = {
    symbol: '', strategy: 'grid', grid_count: 10, base_ma_key: 'MA20',
    grid_spread: 0.10, position_size: 1.0, check_interval: 30, allocated_funds: 30000,
    stop_loss_pct: -5.0, take_profit_pct: 10.0, trend_ma_key: '', dynamic_interval: false,
    max_drawdown_pct: -15.0,
    position_shares: 0, position_avg_cost: 0,
  }
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
  const payload = { ...addForm.value }
  if (!payload.trend_ma_key) payload.trend_ma_key = undefined as any
  const result = await simStore.addAutoTradeTask(symbol, payload)
  if (result.success) {
    showAddForm.value = false
    await simStore.fetchAutoTradeTasks()
  } else {
    addError.value = result.error || '添加失败'
  }
}

function openEditForm(taskId: number) {
  const task = autoTradeTasks.value[taskId]
  if (!task) return
  editingTaskId.value = taskId
  editForm.value = {
    strategy: task.task.strategy ?? 'grid',
    grid_count: task.task.grid_count ?? 10,
    base_ma_key: task.task.base_ma_key ?? 'MA20',
    grid_spread: task.task.grid_spread ?? 0.10,
    position_size: task.task.position_size ?? 1.0,
    check_interval: task.task.check_interval ?? 30,
    allocated_funds: task.task.allocated_funds ?? 30000,
    stop_loss_pct: task.task.stop_loss_pct ?? -5.0,
    take_profit_pct: task.task.take_profit_pct ?? 10.0,
    trend_ma_key: task.task.trend_ma_key ?? '',
    dynamic_interval: task.task.dynamic_interval ?? false,
    max_drawdown_pct: task.task.max_drawdown_pct ?? -15.0,
    position_shares: task.task_position?.shares ?? 0,
    position_avg_cost: task.task_position?.avg_cost ?? 0,
  }
}

async function handleSaveEdit() {
  if (!editingTaskId.value) return
  const payload = { ...editForm.value }
  if (!payload.trend_ma_key) payload.trend_ma_key = undefined as any
  await simStore.updateAutoTradeTask(editingTaskId.value, payload)
  editingTaskId.value = null
  await simStore.fetchAutoTradeTasks()
}

async function handleDeleteTask(taskId: number) {
  const task = autoTradeTasks.value[taskId]
  if (task?.running) {
    await simStore.stopAutoTradeTask(taskId)
  }
  await simStore.deleteAutoTradeTask(taskId)
  await simStore.fetchAutoTradeTasks()
}

async function handleStartTask(taskId: number) {
  await simStore.startAutoTradeTask(taskId)
  await simStore.fetchAutoTradeTasks()
}

async function handleStopTask(taskId: number) {
  await simStore.stopAutoTradeTask(taskId)
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

function getRealtimePrice(symbol: string) {
  const rt = realtimePrices.value[symbol] || realtimePrices.value[stripPrefix(symbol)]
  return rt ? rt.price : null
}

function getRealtimeName(symbol: string): string {
  const rt = realtimePrices.value[symbol] || realtimePrices.value[stripPrefix(symbol)]
  return rt?.name || ''
}

function getPriceChange(symbol: string) {
  const rt = realtimePrices.value[symbol] || realtimePrices.value[stripPrefix(symbol)]
  if (!rt) return null
  const task = autoTradeTasks.value[symbol]
  const sig = task?.signal
  if (!sig?.close) return null
  const change = ((rt.price - sig.close) / sig.close * 100)
  return change
}

function strategyLabel(s: string) {
  const found = strategyOptions.find(o => o.value === s)
  return found ? found.label : s
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
          <label>策略类型</label>
          <select v-model="addForm.strategy" class="input select">
            <option v-for="opt in strategyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <template v-if="isGridStrategy">
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
        </template>
        <template v-else-if="addForm.strategy === 'ma_trend'">
          <div class="form-item">
            <label>快线均线</label>
            <select v-model="addForm.base_ma_key" class="input select">
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
          <div class="form-item">
            <label>慢线均线（趋势过滤）</label>
            <select v-model="addForm.trend_ma_key" class="input select">
              <option value="">不启用</option>
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
        </template>
        <template v-else-if="isBollingerStrategy">
          <div class="form-item">
            <label>趋势过滤均线</label>
            <select v-model="addForm.trend_ma_key" class="input select">
              <option value="">不启用</option>
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
        </template>
        <template v-else-if="isRSIStrategy">
          <div class="form-item">
            <label>超卖阈值</label>
            <input v-model.number="addForm.rsi_oversold" type="number" min="10" max="40" step="5" class="input" />
            <span class="unit">（默认30）</span>
          </div>
          <div class="form-item">
            <label>超买阈值</label>
            <input v-model.number="addForm.rsi_overbought" type="number" min="60" max="90" step="5" class="input" />
            <span class="unit">（默认70）</span>
          </div>
        </template>
        <template v-else-if="isMACDCrossStrategy">
          <div class="form-item">
            <label>趋势过滤均线</label>
            <select v-model="addForm.trend_ma_key" class="input select">
              <option value="">不启用</option>
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
        </template>
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
        <div class="form-item">
          <label>止损触发%</label>
          <input v-model.number="addForm.stop_loss_pct" type="number" min="-20" max="0" step="1" class="input" />
          <span class="unit">%（如-5=亏5%清仓）</span>
        </div>
        <div class="form-item">
          <label>止盈触发%</label>
          <input v-model.number="addForm.take_profit_pct" type="number" min="1" max="50" step="1" class="input" />
          <span class="unit">%（如10=赚10%清仓）</span>
        </div>
        <div class="form-item">
          <label>最大回撤%</label>
          <input v-model.number="addForm.max_drawdown_pct" type="number" min="-50" max="0" step="1" class="input" />
          <span class="unit">%（如-15=回撤15%暂停）</span>
        </div>
        <div class="form-item">
          <label>动态间隔</label>
          <label class="toggle-label">
            <input v-model="addForm.dynamic_interval" type="checkbox" class="checkbox" />
            <span class="toggle-text">{{ addForm.dynamic_interval ? '开启' : '关闭' }}</span>
          </label>
        </div>
        <div class="form-item">
          <label>已持有数量</label>
          <input v-model.number="addForm.position_shares" type="number" min="0" step="100" class="input" placeholder="0" />
          <span class="unit">股（选填）</span>
        </div>
        <div class="form-item">
          <label>持仓成本价</label>
          <input v-model.number="addForm.position_avg_cost" type="number" min="0" step="0.001" class="input" placeholder="0.000" />
          <span class="unit">元/股（选填）</span>
        </div>
      </div>
      <div v-if="addError" class="error-msg">{{ addError }}</div>
      <div class="form-btns">
        <button class="btn-sm cancel-btn" @click="showAddForm = false">取消</button>
        <button class="btn-sm confirm-btn" :disabled="isAutoTrading" @click="handleAddTask">确认添加</button>
      </div>
    </div>

    <!-- Edit Task Form -->
    <div v-if="editingTaskId" class="add-form">
      <h4 class="form-title">编辑任务 · {{ autoTradeTasks[editingTaskId]?.symbol }}</h4>
      <div class="form-grid">
        <div class="form-item">
          <label>策略类型</label>
          <select v-model="editForm.strategy" class="input select">
            <option v-for="opt in strategyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </div>
        <template v-if="editForm.strategy === 'grid'">
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
        </template>
        <template v-else-if="editForm.strategy === 'ma_trend'">
          <div class="form-item">
            <label>快线均线</label>
            <select v-model="editForm.base_ma_key" class="input select">
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
          <div class="form-item">
            <label>慢线均线（趋势过滤）</label>
            <select v-model="editForm.trend_ma_key" class="input select">
              <option value="">不启用</option>
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
        </template>
        <template v-else-if="editForm.strategy === 'bollinger'">
          <div class="form-item">
            <label>趋势过滤均线</label>
            <select v-model="editForm.trend_ma_key" class="input select">
              <option value="">不启用</option>
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
        </template>
        <template v-else-if="editForm.strategy === 'rsi'">
          <div class="form-item">
            <label>超卖阈值</label>
            <input v-model.number="editForm.rsi_oversold" type="number" min="10" max="40" step="5" class="input" />
          </div>
          <div class="form-item">
            <label>超买阈值</label>
            <input v-model.number="editForm.rsi_overbought" type="number" min="60" max="90" step="5" class="input" />
          </div>
        </template>
        <template v-else-if="editForm.strategy === 'macd_cross'">
          <div class="form-item">
            <label>趋势过滤均线</label>
            <select v-model="editForm.trend_ma_key" class="input select">
              <option value="">不启用</option>
              <option v-for="ma in maKeyOptions" :key="ma" :value="ma">{{ ma }}</option>
            </select>
          </div>
        </template>
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
        <div class="form-item">
          <label>止损触发%</label>
          <input v-model.number="editForm.stop_loss_pct" type="number" min="-20" max="0" step="1" class="input" />
          <span class="unit">%（如-5=亏5%清仓）</span>
        </div>
        <div class="form-item">
          <label>止盈触发%</label>
          <input v-model.number="editForm.take_profit_pct" type="number" min="1" max="50" step="1" class="input" />
          <span class="unit">%（如10=赚10%清仓）</span>
        </div>
        <div class="form-item">
          <label>最大回撤%</label>
          <input v-model.number="editForm.max_drawdown_pct" type="number" min="-50" max="0" step="1" class="input" />
          <span class="unit">%（如-15=回撤15%暂停）</span>
        </div>
        <div class="form-item">
          <label>动态间隔</label>
          <label class="toggle-label">
            <input v-model="editForm.dynamic_interval" type="checkbox" class="checkbox" />
            <span class="toggle-text">{{ editForm.dynamic_interval ? '开启' : '关闭' }}</span>
          </label>
        </div>
        <div class="form-item">
          <label>已持有数量</label>
          <input v-model.number="editForm.position_shares" type="number" min="0" step="100" class="input" placeholder="0" />
          <span class="unit">股</span>
        </div>
        <div class="form-item">
          <label>持仓成本价</label>
          <input v-model.number="editForm.position_avg_cost" type="number" min="0" step="0.001" class="input" placeholder="0.000" />
          <span class="unit">元/股</span>
        </div>
      </div>
      <div class="form-btns">
        <button class="btn-sm cancel-btn" @click="editingTaskId = null">取消</button>
        <button class="btn-sm confirm-btn" :disabled="isAutoTrading" @click="handleSaveEdit">保存</button>
      </div>
    </div>

    <!-- Task Cards -->
    <div v-if="taskList.length === 0 && !showAddForm" class="empty-state">
      暂无自动交易任务，点击"添加任务"创建一个
    </div>

    <div v-else class="task-cards"
      @dragover.prevent
      @drop="onContainerDrop">
      <div v-for="ts in taskList" :key="ts.id" :data-task-id="ts.id"
        class="task-card" :class="{ 'drag-over': dragOverId === ts.id, 'dragging': draggedId === ts.id }"
        draggable="true"
        @dragstart="onDragStart($event, ts.id)"
        @dragend="onDragEnd($event)"
        @dragover="onDragOver($event, ts.id)"
        @dragleave="onDragLeave">
        <div class="task-card-header">
          <div class="task-symbol-row">
            <span class="drag-handle" title="拖拽排序">⋮⋮</span>
            <span class="running-indicator" :class="{ running: ts.running }"></span>
            <div class="task-symbol-info">
              <span class="task-name">{{ getRealtimeName(ts.symbol) || ts.task_name || '' }}</span>
              <span class="task-symbol">{{ formatSymbolForDisplay(ts.symbol) }}</span>
            </div>
            <span class="task-strategy">{{ strategyLabel(ts.task.strategy) }}</span>
            <span v-if="ts.task.trend_ma_key" class="task-tag">趋势过滤({{ ts.task.trend_ma_key }})</span>
            <span v-if="ts.task.dynamic_interval" class="task-tag">动态间隔</span>
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
            <div class="param-item">
              <span class="param-label">止盈/止损</span>
              <span class="param-value">
                <span style="color: #26a69a">止{{ ts.task.take_profit_pct ?? 10 }}%</span>
                /
                <span style="color: #ef5350">损{{ (ts.task.stop_loss_pct ?? -5) }}%</span>
              </span>
            </div>
            <div class="param-item">
              <span class="param-label">最大回撤</span>
              <span class="param-value" style="color: #ff9800">
                {{ (ts.task.max_drawdown_pct ?? -15) }}%
              </span>
            </div>
            <div v-if="(ts.task.consecutive_losses ?? 0) > 0" class="param-item">
              <span class="param-label">连续亏损</span>
              <span class="param-value" :style="{ color: (ts.task.consecutive_losses ?? 0) >= 3 ? '#ef5350' : '#ff9800' }">
                {{ ts.task.consecutive_losses }}次
                <span v-if="(ts.task.consecutive_losses ?? 0) >= 1" class="cooldown-tag">冷却延长</span>
              </span>
            </div>
          </div>

          <div v-if="ts.signal" class="task-signal-detail" :style="{ background: signalBg(ts.signal.signal) }">
            <span>{{ ts.signal.action_desc || ts.signal.signal_text }}</span>
            <span class="signal-ratio">建议 {{ Math.floor((ts.signal.position_ratio || 0) * 100) }}%</span>
          </div>

          <div class="task-last-check">
            上次检查: {{ ts.task.last_check || '--' }}
          </div>
        </div>

        <div class="task-card-actions">
          <template v-if="!ts.running">
            <button class="btn-sm edit-btn" :disabled="isAutoTrading" @click="openEditForm(ts.id)">编辑</button>
            <button class="btn-sm start-btn" :disabled="isAutoTrading" @click="handleStartTask(ts.id)">启动</button>
            <button class="btn-sm delete-btn" :disabled="isAutoTrading" @click="handleDeleteTask(ts.id)">删除</button>
          </template>
          <template v-else>
            <button class="btn-sm stop-btn" :disabled="isAutoTrading" @click="handleStopTask(ts.id)">停止</button>
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

.unit { font-size: 11px; color: rgba(255,255,255,0.5); margin-left: 4px; }
.toggle-label { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.toggle-label .checkbox { width: 16px; height: 16px; cursor: pointer; }
.toggle-text { font-size: 12px; color: rgba(255,255,255,0.7); }

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
  cursor: grab;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.15s, border-color 0.15s;

  &:active { cursor: grabbing; }

  &.dragging {
    opacity: 0.4;
    transform: scale(0.97);
    box-shadow: none;
    z-index: 1;
  }

  &.drag-over {
    border-color: var(--accent-cyan);
    box-shadow: 0 0 0 2px rgba(0, 242, 255, 0.25), 0 4px 16px rgba(0, 242, 255, 0.1);
    transform: translateY(-2px);
  }
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

.drag-handle {
  color: rgba(255,255,255,0.2);
  font-size: 14px;
  letter-spacing: -2px;
  cursor: grab;
  flex-shrink: 0;
  user-select: none;
  line-height: 1;

  &:hover { color: rgba(255,255,255,0.45); }
  &:active { cursor: grabbing; color: var(--accent-cyan); }
}

.task-symbol-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.task-symbol {
  font-size: 11px;
  color: var(--text-muted);
}

.task-name {
  font-size: 15px;
  font-weight: bold;
  color: var(--text-primary);
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
.tag-stopped { background: rgba(158,158,158,0.2); color: #9e9e9e; }
.tag-filter { background: rgba(33,150,243,0.15); color: #42a5f5; }
.tag-dynamic { background: rgba(255,183,77,0.15); color: #ffb74d; }
.strategy-tag { background: rgba(149,117,205,0.15); color: #9575cd; }
.task-tag { font-size: 11px; color: #42a5f5; background: rgba(33,150,243,0.1); padding: 1px 6px; border-radius: 3px; }
.cooldown-tag { font-size: 10px; color: #ff9800; background: rgba(255,152,0,0.1); padding: 1px 5px; border-radius: 3px; margin-left: 4px; }
</style>