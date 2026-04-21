<script setup lang="ts">
import { computed } from 'vue'
import type { LatestIndicator, GridSignal } from '@/services/stockService'

const props = defineProps<{
  tradeSignal: string
  latest?: LatestIndicator
  gridSignal?: GridSignal
  realtimePrice?: number
  changePct?: number
}>()

const signalClass = computed(() => {
  if (props.tradeSignal === '买入') return 'buy'
  if (props.tradeSignal === '卖出') return 'sell'
  return 'watch'
})

const displayPrice = computed(() => {
  if (props.realtimePrice) return props.realtimePrice.toFixed(3)
  if (props.latest) return props.latest['收盘'].toFixed(3)
  return '-'
})

const displayChange = computed(() => {
  const pct = props.changePct ?? props.latest?.['涨跌幅'] ?? 0
  const sign = pct >= 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
})

const rsiStatus = computed(() => {
  const rsi = props.latest?.['RSI'] ?? 0
  if (rsi > 70) return { text: '超买', class: 'warn' }
  if (rsi < 30) return { text: '超卖', class: 'good' }
  return { text: '正常', class: 'normal' }
})

const kdjStatus = computed(() => {
  const j = props.latest?.['J'] ?? 0
  if (j > 80) return { text: '超买', class: 'warn' }
  if (j < 20) return { text: '超卖', class: 'good' }
  return { text: '正常', class: 'normal' }
})
</script>

<template>
  <div class="trade-signal-bar" :class="`signal-${signalClass}`">
    <div class="signal-main">
      <span class="signal-label">今日交易信号</span>
      <span class="signal-value" :class="signalClass">{{ tradeSignal }}</span>
      <span class="signal-price">{{ displayPrice }}</span>
      <span class="signal-change" :class="changePct !== undefined ? (changePct >= 0 ? 'up' : 'down') : (latest && latest['涨跌幅'] >= 0 ? 'up' : 'down')">
        {{ displayChange }}
      </span>
    </div>
    <div class="signal-detail">
      <span>RSI: <span :class="rsiStatus.class">{{ rsiStatus.text }}</span></span>
      <span>KDJ: <span :class="kdjStatus.class">{{ kdjStatus.text }}</span></span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.trade-signal-bar {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px 24px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.3s;

  &.signal-buy {
    border-color: #26a69a;
    background: linear-gradient(135deg, rgba(38, 166, 154, 0.15) 0%, var(--bg-card) 100%);
  }

  &.signal-sell {
    border-color: #ef5350;
    background: linear-gradient(135deg, rgba(239, 83, 80, 0.15) 0%, var(--bg-card) 100%);
  }

  &.signal-watch {
    border-color: #FF9800;
    background: linear-gradient(135deg, rgba(255, 152, 0, 0.15) 0%, var(--bg-card) 100%);
  }
}

.signal-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
}

.signal-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.signal-value {
  font-size: 20px;
  font-weight: bold;

  &.buy { color: #26a69a; }
  &.sell { color: #ef5350; }
  &.watch { color: #FF9800; }
}

.signal-price {
  font-size: 16px;
  color: var(--text-primary);
  font-weight: bold;
}

.signal-change {
  font-size: 14px;

  &.up { color: #ef5350; }
  &.down { color: #26a69a; }
}

.signal-detail {
  font-size: 13px;
  color: var(--text-secondary);
  flex: 1;

  span {
    margin-right: 20px;
  }

  .good { color: #26a69a; }
  .warn { color: #FF9800; }
  .normal { color: var(--text-secondary); }
}
</style>
