<script setup lang="ts">
import { ref } from 'vue'
import type { TradeRecord } from '@/services/stockService'

const props = defineProps<{
  trades: TradeRecord[]
}>()

const showDetails = ref(false)
</script>

<template>
  <div class="sim-trade">
    <div class="trade-header" @click="showDetails = !showDetails">
      <h3 class="section-title">交易记录 ({{ trades.length }}笔)</h3>
      <span class="toggle-icon">{{ showDetails ? '▲' : '▼' }}</span>
    </div>

    <div v-if="showDetails" class="trade-table-wrap">
      <table class="trade-table">
        <thead>
          <tr>
            <th>进场日期</th>
            <th>进场价格</th>
            <th>网格层</th>
            <th>出场日期</th>
            <th>出场价格</th>
            <th>网格层</th>
            <th>股数</th>
            <th>盈亏</th>
            <th>收益率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(t, i) in trades" :key="i">
            <td>{{ t.entry_date }}</td>
            <td>{{ t.entry_price.toFixed(3) }}</td>
            <td>{{ t.entry_grid }}</td>
            <td>{{ t.exit_date }}</td>
            <td>{{ t.exit_price.toFixed(3) }}</td>
            <td>{{ t.exit_grid }}</td>
            <td>{{ t.shares }}</td>
            <td :style="{ color: t.pnl >= 0 ? '#26a69a' : '#ef5350' }">
              {{ t.pnl >= 0 ? '+' : '' }}{{ t.pnl.toFixed(2) }}
            </td>
            <td :style="{ color: t.pnl_pct >= 0 ? '#26a69a' : '#ef5350' }">
              {{ t.pnl_pct >= 0 ? '+' : '' }}{{ (t.pnl_pct * 100).toFixed(2) }}%
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.sim-trade {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.trade-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
}

.section-title {
  color: #7986cb;
  font-size: 15px;
  margin: 0;
}

.toggle-icon {
  color: #7986cb;
  font-size: 12px;
}

.trade-table-wrap {
  overflow-x: auto;
  border-top: 1px solid var(--border-color);
}

.trade-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td {
    padding: 10px 16px;
    text-align: center;
    white-space: nowrap;
  }

  th {
    background: var(--bg-hover);
    color: #7986cb;
    font-weight: normal;
    font-size: 12px;
  }

  tr:not(:last-child) td {
    border-bottom: 1px solid var(--border-color);
  }

  td {
    color: var(--text-primary);
  }
}
</style>
