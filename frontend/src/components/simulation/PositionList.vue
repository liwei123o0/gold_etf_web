<script setup lang="ts">
import { computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { storeToRefs } from 'pinia'

const simStore = useSimulationStore()
const { positions } = storeToRefs(simStore)

const posColor = (pnl: number) => pnl >= 0 ? '#ef5350' : '#26a69a'
const posSign = (pnl: number) => pnl >= 0 ? '+' : ''

async function closePosition(symbol: string, shares: number, price: number, name: string) {
  await simStore.sell(symbol, name, price, shares)
}
</script>

<template>
  <div class="position-list">
    <div class="panel-header">
      <h3 class="section-title">持仓明细 ({{ positions.length }})</h3>
      <button 
        v-if="positions.length > 0"
        class="close-all-btn"
        @click="simStore.closeAll()"
      >全部清仓</button>
    </div>

    <div v-if="positions.length === 0" class="empty-pos">
      暂无持仓
    </div>

    <div v-else class="pos-table-wrap">
      <table class="pos-table">
        <thead>
          <tr>
            <th>证券</th>
            <th>持仓量</th>
            <th>成本价</th>
            <th>当前价</th>
            <th>市值</th>
            <th>浮动盈亏</th>
            <th>盈亏%</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in positions" :key="p.symbol">
            <td>
              <div class="sym-name">{{ p.name }}</div>
              <div class="sym-code">{{ p.symbol }}</div>
            </td>
            <td>{{ p.shares }}</td>
            <td>{{ p.avg_cost.toFixed(3) }}</td>
            <td>{{ p.current_price.toFixed(3) }}</td>
            <td>{{ (p.shares * p.current_price).toFixed(2) }}</td>
            <td :style="{ color: posColor(p.unrealized_pnl) }">
              {{ posSign(p.unrealized_pnl) }}{{ p.unrealized_pnl.toFixed(2) }}
            </td>
            <td :style="{ color: posColor(p.unrealized_pnl_pct) }">
              {{ posSign(p.unrealized_pnl_pct) }}{{ p.unrealized_pnl_pct.toFixed(2) }}%
            </td>
            <td>
              <button class="sell-btn" @click="closePosition(p.symbol, p.shares, p.current_price, p.name)">
                卖出
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.position-list {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.section-title {
  color: #7986cb;
  font-size: 15px;
  margin: 0;
}

.close-all-btn {
  padding: 4px 12px;
  background: rgba(239, 83, 80, 0.1);
  border: 1px solid #ef5350;
  border-radius: 4px;
  color: #ef5350;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(239, 83, 80, 0.2);
  }
}

.empty-pos {
  padding: 32px;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
}

.pos-table-wrap {
  overflow-x: auto;
}

.pos-table {
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

.sym-name {
  font-weight: 500;
}

.sym-code {
  color: var(--text-muted);
  font-size: 11px;
}

.sell-btn {
  padding: 4px 12px;
  background: rgba(38, 166, 154, 0.15);
  border: 1px solid #26a69a;
  border-radius: 4px;
  color: #26a69a;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(38, 166, 154, 0.25);
  }
}
</style>
