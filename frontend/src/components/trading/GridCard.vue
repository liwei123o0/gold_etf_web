<script setup lang="ts">
import { ref, computed } from 'vue'
import type { GridSignal } from '@/services/stockService'

const props = defineProps<{
  gridSignal?: GridSignal
  allGridSignals?: Record<string, GridSignal>
  selectedMa?: string
}>()

const emit = defineEmits<{
  maChange: [maKey: string]
}>()

const maOptions = ['MA5', 'MA10', 'MA20', 'MA60', 'MACD', 'MACD_SIGNAL']
const expandedMa = ref<string | null>(null)

const currentGrid = computed(() => {
  return props.gridSignal
})

const signalClass = computed(() => {
  const signal = currentGrid.value?.signal || '持有'
  if (signal === '买入') return 'buy'
  if (signal === '卖出') return 'sell'
  return 'hold'
})

const signalColor = computed(() => {
  const signal = currentGrid.value?.signal || '持有'
  if (signal === '买入') return '#26a69a'
  if (signal === '卖出') return '#ef5350'
  return '#FF9800'
})

const gridCells = computed(() => {
  if (!currentGrid.value) return []
  const n = currentGrid.value.total_grids || 10
  const cur = currentGrid.value.current_grid || 0
  return Array.from({ length: n }, (_, i) => ({
    filled: i < cur,
    current: i === cur
  }))
})

const positionPct = computed(() => {
  return Math.round((currentGrid.value?.position_ratio || 0) * 100)
})

const positionColor = computed(() => {
  if (positionPct.value >= 70) return '#26a69a'
  if (positionPct.value >= 40) return '#FF9800'
  return '#ef5350'
})

const atrDisplay = computed(() => {
  const g = currentGrid.value
  if (!g?.atr) return { text: '无数据', color: 'var(--text-muted)' }
  return {
    text: `${g.atr.toFixed(4)} (${g.atr_pct?.toFixed(2)}%)`,
    color: 'var(--accent-purple)'
  }
})

const devDisplay = computed(() => {
  const g = currentGrid.value
  if (g?.ma_deviation_pct === undefined || g?.ma_deviation_pct === null) {
    return { text: '-', color: 'var(--text-muted)' }
  }
  const dev = g.ma_deviation_pct
  return {
    text: `${dev > 0 ? '+' : ''}${dev.toFixed(2)}%`,
    color: dev > 0 ? '#26a69a' : '#ef5350'
  }
})

const actionEmoji = computed(() => {
  const signal = currentGrid.value?.signal || '持有'
  return { '买入': '📈', '卖出': '📉', '持有': '➡️' }[signal] || '➡️'
})

const actionClass = computed(() => {
  const signal = currentGrid.value?.signal || '持有'
  return { '买入': 'action-buy', '卖出': 'action-sell', '持有': 'action-hold' }[signal] || 'action-hold'
})

function onMaChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('maChange', target.value)
}

function toggleExpand() {
  expandedMa.value = expandedMa.value ? null : props.selectedMa || 'MA20'
}
</script>

<template>
  <div class="grid-card" :class="`signal-${signalClass}`">
    <div class="grid-card-header">
      <div class="header-title">
        <span class="title-text">网格交易策略</span>
        <span v-if="currentGrid?.dynamic_spread" class="dynamic-badge">ATR动态</span>
        <span v-else class="dynamic-badge static">固定参数</span>
      </div>
      <div class="ma-selector">
        <span class="ma-label">基准均线</span>
        <select :value="selectedMa || 'MA20'" @change="onMaChange">
          <option v-for="opt in maOptions" :key="opt" :value="opt">{{ opt }}</option>
        </select>
      </div>
    </div>

    <div class="grid-card-body">
      <div class="grid-visual">
        <div class="grid-bar-wrapper">
          <div class="grid-bar-bg">
            <div
              v-for="(cell, i) in gridCells"
              :key="i"
              class="grid-bar-cell"
              :class="{ filled: cell.filled, current: cell.current }"
            ></div>
          </div>
          <div
            class="grid-bar-pointer"
            :style="{ left: `${((currentGrid?.current_grid || 0) + 0.5) / (currentGrid?.total_grids || 10) * 100}%` }"
          ></div>
        </div>
        <div class="grid-labels">
          <span>{{ currentGrid?.lower_bound?.toFixed(3) || '-' }} (底)</span>
          <span class="current-price" :style="{ color: signalColor }">
            {{ currentGrid?.close?.toFixed(4) || '-' }}
          </span>
          <span>{{ currentGrid?.upper_bound?.toFixed(3) || '-' }} (顶)</span>
        </div>
      </div>

      <div class="grid-info">
        <div class="grid-stat-row">
          <span class="stat-label">建议持仓</span>
          <span class="stat-value" :style="{ color: positionColor }">{{ positionPct }}%</span>
        </div>
        <div class="grid-stat-row">
          <span class="stat-label">网格区间</span>
          <span class="stat-value">±{{ currentGrid?.grid_spread_pct?.toFixed(1) || '-' }}%</span>
        </div>
        <div class="grid-stat-row">
          <span class="stat-label">每格步长</span>
          <span class="stat-value">{{ currentGrid?.step_pct?.toFixed(2) || '-' }}%/格</span>
        </div>
        <div class="grid-stat-row">
          <span class="stat-label">ATR(20日)</span>
          <span class="stat-value" :style="{ color: atrDisplay.color }">{{ atrDisplay.text }}</span>
        </div>
        <div class="grid-stat-row">
          <span class="stat-label">偏离{{ selectedMa }}</span>
          <span class="stat-value" :style="{ color: devDisplay.color }">{{ devDisplay.text }}</span>
        </div>
      </div>
    </div>

    <div class="grid-card-footer">
      <span class="action-icon">{{ actionEmoji }}</span>
      <span class="action-text" :class="actionClass">{{ currentGrid?.signal || '持有' }}</span>
      <span class="action-desc">：{{ currentGrid?.action_desc || '' }}</span>
      <span class="position-info">📍 第{{ currentGrid?.current_grid || 0 }}格/共{{ currentGrid?.total_grids || 0 }}格</span>
    </div>

    <!-- 展开查看其他均线信号 -->
    <button class="expand-btn" @click="toggleExpand">
      {{ expandedMa ? '收起' : '查看' }}各均线信号
    </button>

    <div v-if="expandedMa && allGridSignals" class="grid-comparison">
      <div v-for="(grid, maKey) in allGridSignals" :key="maKey" class="comparison-row" :class="{ active: maKey === selectedMa }">
        <span class="ma-key">{{ maKey }}</span>
        <span class="grid-signal" :class="grid.signal === '买入' ? 'buy' : grid.signal === '卖出' ? 'sell' : 'hold'">
          {{ grid.signal }}
        </span>
        <span class="grid-price">{{ grid.close?.toFixed(4) || '-' }}</span>
        <span class="grid-position">持仓{{ Math.round(grid.position_ratio * 100) }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.grid-card {
  background: var(--bg-card);
  border: 2px solid var(--border-color);
  border-radius: 12px;
  margin-bottom: 20px;
  overflow: hidden;
  transition: border-color 0.3s;

  &.signal-buy { border-color: #26a69a; }
  &.signal-sell { border-color: #ef5350; }
  &.signal-hold { border-color: #FF9800; }
}

.grid-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--border-color);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-text {
  font-size: 15px;
  font-weight: bold;
  color: var(--text-primary);
}

.dynamic-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(102, 126, 234, 0.3);
  color: var(--accent-purple);
  font-weight: normal;

  &.static {
    background: rgba(255, 152, 0, 0.2);
    color: #FF9800;
  }
}

.ma-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ma-label {
  font-size: 12px;
  color: var(--text-secondary);
}

select {
  padding: 4px 28px 4px 10px;
  background: rgba(20, 25, 45, 0.95);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  outline: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%237986cb' d='M6 8L2 4h8z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;

  &:focus {
    border-color: var(--accent-purple);
  }
}

.grid-card-body {
  display: flex;
  gap: 20px;
  padding: 16px 20px;
}

.grid-visual {
  flex: 1;
  min-width: 0;
}

.grid-bar-wrapper {
  position: relative;
  height: 36px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 6px;
}

.grid-bar-bg {
  position: absolute;
  inset: 0;
  display: flex;
}

.grid-bar-cell {
  flex: 1;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  transition: background 0.3s;

  &:last-child { border-right: none; }

  &.filled {
    background: rgba(38, 166, 154, 0.4);
  }

  &.current {
    background: var(--accent-purple) !important;
    box-shadow: 0 0 8px rgba(102, 126, 234, 0.6);
  }
}

.grid-bar-pointer {
  position: absolute;
  top: -6px;
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid #fff;
  transform: translateX(-50%);
  transition: left 0.3s;
}

.grid-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;

  .current-price {
    font-weight: bold;
    font-size: 12px;
  }
}

.grid-info {
  width: 160px;
  flex-shrink: 0;
}

.grid-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid var(--border-color);

  &:last-child { border-bottom: none; }
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.stat-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: bold;
}

.grid-card-footer {
  padding: 12px 20px;
  font-size: 13px;
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.15);
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 8px;

  .action-icon {
    font-size: 16px;
  }

  .action-text {
    font-weight: bold;

    &.action-buy { color: #26a69a; }
    &.action-sell { color: #ef5350; }
    &.action-hold { color: #FF9800; }
  }

  .action-desc {
    flex: 1;
  }

  .position-info {
    color: var(--text-muted);
  }
}

.expand-btn {
  width: 100%;
  padding: 10px;
  background: rgba(255, 255, 255, 0.02);
  border: none;
  border-top: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(102, 126, 234, 0.1);
    color: var(--accent-purple);
  }
}

.grid-comparison {
  border-top: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.2);
}

.comparison-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border-color);
  font-size: 12px;

  &:last-child {
    border-bottom: none;
  }

  &.active {
    background: rgba(102, 126, 234, 0.1);
  }

  .ma-key {
    font-weight: bold;
    color: var(--text-primary);
    min-width: 80px;
  }

  .grid-signal {
    font-weight: bold;

    &.buy { color: #26a69a; }
    &.sell { color: #ef5350; }
    &.hold { color: #FF9800; }
  }

  .grid-price {
    color: var(--text-secondary);
  }

  .grid-position {
    color: var(--text-muted);
    margin-left: auto;
  }
}
</style>