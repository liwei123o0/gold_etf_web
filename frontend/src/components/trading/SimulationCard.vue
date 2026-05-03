<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { stockService } from '@/services/stockService'
import type { BacktestRequest, BacktestResponse } from '@/services/stockService'
import EquityCurveChart from '@/components/charts/EquityCurveChart.vue'

const props = defineProps<{
  symbol: string
  startDate?: string | null
  endDate?: string | null
}>()

const emit = defineEmits<{
  running: [boolean]
}>()

const params = reactive<BacktestRequest>({
  symbol: props.symbol,
  start_date: props.startDate || undefined,
  end_date: props.endDate || undefined,
  initial_capital: 100000,
  grid_count: 10,
  spread_type: 'fixed',
  base_ma_key: 'MA20'
})

const isRunning = ref(false)
const result = ref<BacktestResponse | null>(null)
const errorMsg = ref('')
const showDetails = ref(false)

const gridCountOptions = [
  { label: '5格', value: 5 },
  { label: '10格', value: 10 },
  { label: '15格', value: 15 },
  { label: '20格', value: 20 }
]

const spreadOptions = [
  { label: '固定(±5%)', value: 'fixed' },
  { label: 'ATR动态', value: 'atr' }
]

const maOptions = [
  { label: 'MA5', value: 'MA5' },
  { label: 'MA10', value: 'MA10' },
  { label: 'MA20', value: 'MA20' },
  { label: 'MA60', value: 'MA60' }
]

const returnClass = computed(() => {
  if (!result.value) return ''
  return result.value.total_return_pct >= 0 ? 'positive' : 'negative'
})

const returnColor = computed(() => {
  if (!result.value) return 'var(--text-primary)'
  return result.value.total_return_pct >= 0 ? '#ef5350' : '#26a69a'
})

async function runBacktest() {
  isRunning.value = true
  errorMsg.value = ''
  result.value = null
  showDetails.value = false
  emit('running', true)

  try {
    const data = await stockService.runBacktest({
      ...params,
      symbol: props.symbol,
      start_date: props.startDate || undefined,
      end_date: props.endDate || undefined
    })
    result.value = data
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || '回测执行失败'
  } finally {
    isRunning.value = false
    emit('running', false)
  }
}

function toggleDetails() {
  showDetails.value = !showDetails.value
}
</script>

<template>
  <div class="simulation-card">
    <div class="sim-header">
      <span class="sim-title">模拟交易回测</span>
      <button class="run-btn" :disabled="isRunning" @click="runBacktest">
        {{ isRunning ? '运行中...' : '运行回测' }}
      </button>
    </div>

    <div class="sim-params">
      <div class="param-group">
        <label>初始资金</label>
        <input v-model.number="params.initial_capital" type="number" min="10000" step="10000" />
        <span class="unit">元</span>
      </div>

      <div class="param-group">
        <label>网格数量</label>
        <select v-model.number="params.grid_count">
          <option v-for="opt in gridCountOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>

      <div class="param-group">
        <label>网格区间</label>
        <select v-model="params.spread_type">
          <option v-for="opt in spreadOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>

      <div class="param-group">
        <label>基准均线</label>
        <select v-model="params.base_ma_key">
          <option v-for="opt in maOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="isRunning" class="sim-loading">
      <div class="spinner"></div>
      <span>回测运行中...</span>
    </div>

    <div v-if="errorMsg" class="sim-error">{{ errorMsg }}</div>

    <div v-if="result" class="sim-results">
      <div class="sim-kpis">
        <div class="kpi kpi-large">
          <span class="kpi-label">总收益率</span>
          <span class="kpi-value" :style="{ color: returnColor }">
            {{ result.total_return_pct >= 0 ? '+' : '' }}{{ result.total_return_pct.toFixed(2) }}%
          </span>
        </div>
        <div class="kpi">
          <span class="kpi-label">最终资金</span>
          <span class="kpi-value">{{ result.final_equity.toFixed(2) }}</span>
        </div>
        <div class="kpi">
          <span class="kpi-label">交易次数</span>
          <span class="kpi-value">{{ result.num_trades }}</span>
        </div>
        <div class="kpi">
          <span class="kpi-label">胜率</span>
          <span class="kpi-value" :style="{ color: result.win_rate >= 0.5 ? '#26a69a' : '#ef5350' }">
            {{ (result.win_rate * 100).toFixed(1) }}%
          </span>
        </div>
        <div class="kpi">
          <span class="kpi-label">最大回撤</span>
          <span class="kpi-value" style="color: #ef5350;">{{ result.max_drawdown_pct.toFixed(2) }}%</span>
        </div>
      </div>

      <EquityCurveChart v-if="result.equity_curve.length > 0" :data="result.equity_curve" title="资金曲线" />

      <div class="sim-toggle">
        <button class="toggle-btn" @click="toggleDetails">
          {{ showDetails ? '收起' : '查看' }}交易记录 ({{ result.trade_history.length }}笔)
        </button>
      </div>

      <div v-if="showDetails" class="sim-trade-table">
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>序号</th>
                <th>买入日期</th>
                <th>买入价格</th>
                <th>网格层</th>
                <th>卖出日期</th>
                <th>卖出价格</th>
                <th>盈亏(元)</th>
                <th>盈亏率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(trade, i) in result.trade_history" :key="i">
                <td>{{ i + 1 }}</td>
                <td>{{ trade.entry_date }}</td>
                <td>{{ trade.entry_price.toFixed(3) }}</td>
                <td>{{ trade.entry_grid }}</td>
                <td>{{ trade.exit_date }}</td>
                <td>{{ trade.exit_price.toFixed(3) }}</td>
                <td :class="trade.pnl >= 0 ? 'positive' : 'negative'">
                  {{ trade.pnl >= 0 ? '+' : '' }}{{ trade.pnl.toFixed(2) }}
                </td>
                <td :class="trade.pnl_pct >= 0 ? 'positive' : 'negative'">
                  {{ trade.pnl_pct >= 0 ? '+' : '' }}{{ trade.pnl_pct.toFixed(2) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.simulation-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.sim-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.sim-title {
  font-size: 16px;
  font-weight: bold;
  color: var(--text-primary);
}

.run-btn {
  padding: 8px 20px;
  background: linear-gradient(135deg, var(--accent-purple) 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover:not(:disabled) {
    opacity: 0.85;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.sim-params {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}

.param-group {
  display: flex;
  align-items: center;
  gap: 8px;

  label {
    font-size: 13px;
    color: var(--text-secondary);
  }

  input, select {
    padding: 6px 28px 6px 10px;
    background: rgba(20, 25, 45, 0.95);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 13px;
    outline: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%237986cb' d='M6 8L2 4h8z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;

    &:focus {
      border-color: var(--accent-purple);
    }
  }

  input {
    width: 100px;
  }

  .unit {
    color: var(--text-muted);
    font-size: 12px;
  }
}

.sim-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-secondary);

  .spinner {
    width: 24px;
    height: 24px;
    border: 2px solid var(--border-color);
    border-top-color: var(--accent-purple);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.sim-error {
  padding: 12px;
  background: rgba(255, 83, 112, 0.1);
  border: 1px solid rgba(255, 83, 112, 0.3);
  border-radius: 8px;
  color: #ff5370;
  font-size: 13px;
}

.sim-results {
  margin-top: 20px;
}

.sim-kpis {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}

.kpi {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  min-width: 100px;

  &.kpi-large {
    min-width: 140px;
    padding: 16px 20px;
    background: rgba(102, 126, 234, 0.1);
    border: 1px solid var(--border-color);
  }
}

.kpi-label {
  font-size: 12px;
  color: var(--text-muted);
}

.kpi-value {
  font-size: 18px;
  font-weight: bold;
  color: var(--text-primary);

  &.positive { color: #26a69a; }
  &.negative { color: #ef5350; }
}

.sim-toggle {
  margin-bottom: 16px;
}

.toggle-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-purple);
    color: var(--accent-purple);
  }
}

.sim-trade-table {
  margin-top: 16px;

  h4 {
    font-size: 14px;
    color: var(--text-secondary);
    margin-bottom: 12px;
  }
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td {
    padding: 10px 12px;
    text-align: center;
    border-bottom: 1px solid var(--border-color);
  }

  th {
    color: var(--text-muted);
    font-weight: normal;
    background: rgba(255, 255, 255, 0.02);
  }

  td {
    color: var(--text-primary);
  }

  .positive { color: #26a69a; }
  .negative { color: #ef5350; }
}
</style>