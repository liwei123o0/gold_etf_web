<script setup lang="ts">
import { computed } from 'vue'
import type { LatestIndicator } from '@/services/stockService'

const props = defineProps<{
  latest?: LatestIndicator
  realtimePrice?: number
  changePct?: number
}>()

const cards = computed(() => {
  if (!props.latest) return []

  const l = props.latest
  const price = props.realtimePrice ?? l['收盘']
  const change = props.changePct ?? l['涨跌幅']

  return [
    {
      label: '最新价',
      value: price.toFixed(3),
      change: change,
      icon: change >= 0 ? '📈' : '📉'
    },
    {
      label: 'MA5 短期',
      value: l['MA5'].toFixed(3),
      sub: l['收盘'] > l['MA5'] ? '价格>均线↑' : '价格<均线↓',
      icon: l['收盘'] > l['MA5'] ? '✅' : '⚠️'
    },
    {
      label: 'MA10 中期',
      value: l['MA10'].toFixed(3),
      sub: l['MA5'] > l['MA10'] ? '多头排列' : '空头排列',
      icon: l['MA5'] > l['MA10'] ? '✅' : '⚠️'
    },
    {
      label: 'RSI',
      value: l['RSI'].toFixed(1),
      sub: l['RSI'] > 70 ? '超买⚠️' : l['RSI'] < 30 ? '超卖📈' : '正常区间',
      icon: l['RSI'] > 70 ? '⚠️' : l['RSI'] < 30 ? '📈' : '➡️'
    },
    {
      label: 'KDJ J值',
      value: l['J'].toFixed(1),
      sub: l['J'] > 80 ? '超买⚠️' : l['J'] < 20 ? '超卖📈' : '正常',
      icon: l['J'] > 80 ? '⚠️' : l['J'] < 20 ? '📈' : '➡️'
    },
    {
      label: '资金流向',
      value: (l['累计净流入'] / 1e8).toFixed(2) + '亿',
      sub: l['累计净流入'] > 0 ? '净流入↑' : '净流出↓',
      icon: l['累计净流入'] > 0 ? '✅' : '⚠️'
    }
  ]
})
</script>

<template>
  <div class="summary-cards">
    <div v-for="card in cards" :key="card.label" class="card">
      <h3>{{ card.icon }} {{ card.label }}</h3>
      <div class="value">{{ card.value }}</div>
      <div class="sub">{{ card.sub }}</div>
      <div v-if="card.change !== undefined" class="change" :class="card.change >= 0 ? 'up' : 'down'">
        {{ card.change >= 0 ? '+' : '' }}{{ card.change.toFixed(2) }}%
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  transition: all 0.2s;

  &:hover {
    border-color: var(--accent-purple);
    transform: translateY(-2px);
  }

  h3 {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
    font-weight: normal;
  }

  .value {
    font-size: 20px;
    font-weight: bold;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .sub {
    font-size: 11px;
    color: var(--text-muted);
  }

  .change {
    font-size: 13px;
    margin-top: 6px;

    &.up { color: #ef5350; }
    &.down { color: #26a69a; }
  }
}
</style>
