<script setup lang="ts">
import { ref } from 'vue'
import type { SimulationOrder } from '@/services/stockService'

const props = defineProps<{
  orders: SimulationOrder[]
}>()

const showDetails = ref(true)
</script>

<template>
  <div class="sim-order-history">
    <div class="order-header" @click="showDetails = !showDetails">
      <h3 class="section-title">成交记录 ({{ orders.length }}笔)</h3>
      <span class="toggle-icon">{{ showDetails ? '▲' : '▼' }}</span>
    </div>

    <div v-if="showDetails && orders.length > 0" class="order-table-wrap">
      <table class="order-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>方向</th>
            <th>证券</th>
            <th>价格</th>
            <th>数量</th>
            <th>手续费</th>
            <th>盈亏</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in orders" :key="o.id">
            <td>{{ o.timestamp }}</td>
            <td :style="{ color: o.direction === 'buy' ? '#ef5350' : '#26a69a' }">
              {{ o.direction === 'buy' ? '买入' : '卖出' }}
            </td>
            <td>
              <div>{{ o.name }}</div>
              <div class="sym-code">{{ o.symbol }}</div>
            </td>
            <td>{{ o.price.toFixed(3) }}</td>
            <td>{{ o.shares }}</td>
            <td>{{ o.commission.toFixed(2) }}</td>
            <td :style="{ color: o.pnl >= 0 ? '#26a69a' : '#ef5350' }">
              {{ o.pnl >= 0 ? '+' : '' }}{{ o.pnl.toFixed(2) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="orders.length === 0" class="empty-msg">
      暂无成交记录
    </div>
  </div>
</template>

<style scoped lang="scss">
.sim-order-history {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.order-header {
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

.order-table-wrap {
  overflow-x: auto;
  border-top: 1px solid var(--border-color);
}

.order-table {
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

.sym-code {
  color: var(--text-muted);
  font-size: 11px;
}

.empty-msg {
  padding: 24px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
