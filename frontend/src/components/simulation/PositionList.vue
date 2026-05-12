<script setup lang="ts">
import { computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { storeToRefs } from 'pinia'
import { formatSymbolForDisplay } from '@/utils/symbol'

const simStore = useSimulationStore()
const { positions } = storeToRefs(simStore)

const posColor = (pnl: number) => pnl >= 0 ? '#ef5350' : '#26a69a'
const posSign = (pnl: number) => pnl >= 0 ? '+' : ''

const STRATEGY_LABELS: Record<string, string> = {
  manual: '手动交易',
  grid: '网格策略',
  ma_trend: '均线趋势',
}

function getStrategyLabel(type: string): string {
  return STRATEGY_LABELS[type] || type
}

function getStrategyClass(type: string): string {
  if (type === 'manual') return 'manual'
  return 'auto'
}

async function closePosition(symbol: string, shares: number, price: number, name: string) {
  await simStore.sell(symbol, name, price, shares)
}

async function deletePosition(symbol: string, strategy: string) {
  if (confirm(`确定要删除 ${symbol} (${getStrategyLabel(strategy)}) 的持仓记录吗？\n此操作不会生成卖出订单，持仓数据将直接删除。`)) {
    await simStore.deletePosition(symbol, strategy)
  }
}

async function clearAllPositions() {
  if (confirm('确定要清空所有持仓记录吗？\n此操作不会生成卖出订单，所有持仓数据将直接删除。')) {
    await simStore.clearPositions()
  }
}
</script>

<template>
  <div class="position-list">
    <div class="panel-header">
      <h3 class="section-title">持仓明细 ({{ positions.length }})</h3>
      <div class="header-actions">
        <button 
          v-if="positions.length > 0"
          class="clear-btn"
          @click="clearAllPositions"
        >清空持仓</button>
        <button 
          v-if="positions.length > 0"
          class="close-all-btn"
          @click="simStore.closeAll()"
        >全部清仓</button>
      </div>
    </div>

    <div v-if="positions.length === 0" class="empty-pos">
      暂无持仓
    </div>

    <div v-else class="pos-table-wrap">
      <table class="pos-table">
        <thead>
          <tr>
            <th>证券</th>
            <th>策略类型</th>
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
          <tr v-for="p in positions" :key="p.symbol + '-' + p.strategy_type">
            <td>
              <div class="sym-name">{{ p.name }}</div>
              <div class="sym-code">{{ formatSymbolForDisplay(p.symbol) }}</div>
            </td>
            <td>
              <span class="strategy-badge" :class="getStrategyClass(p.strategy_type)">
                {{ getStrategyLabel(p.strategy_type) }}
              </span>
            </td>
            <td>{{ p.shares }}</td>
            <td>{{ p.avg_cost.toFixed(3) }}</td>
            <td>{{ p.current_price.toFixed(3) }}</td>
            <td>{{ (p.market_value ?? p.shares * p.current_price).toFixed(2) }}</td>
            <td :style="{ color: posColor(p.unrealized_pnl) }">
              {{ posSign(p.unrealized_pnl) }}{{ p.unrealized_pnl.toFixed(2) }}
            </td>
            <td :style="{ color: posColor(p.unrealized_pnl_pct) }">
              {{ posSign(p.unrealized_pnl_pct) }}{{ p.unrealized_pnl_pct.toFixed(2) }}%
            </td>
            <td>
              <div class="action-btns">
                <button class="sell-btn" @click="closePosition(p.symbol, p.shares, p.current_price, p.name)">
                  卖出
                </button>
                <button class="delete-btn" @click="deletePosition(p.symbol, p.strategy_type)">
                  删除
                </button>
              </div>
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

.header-actions {
  display: flex;
  gap: 8px;
}

.clear-btn {
  padding: 4px 12px;
  background: rgba(255, 152, 0, 0.1);
  border: 1px solid #ff9800;
  border-radius: 4px;
  color: #ff9800;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 152, 0, 0.2);
  }
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

.delete-btn {
  padding: 4px 10px;
  background: rgba(158, 158, 158, 0.1);
  border: 1px solid #9e9e9e;
  border-radius: 4px;
  color: #9e9e9e;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(158, 158, 158, 0.2);
    color: #ef5350;
    border-color: #ef5350;
  }
}

.action-btns {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.strategy-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: bold;
  white-space: nowrap;

  &.manual {
    background: rgba(121, 134, 203, 0.15);
    color: #7986cb;
  }

  &.auto {
    background: rgba(0, 242, 255, 0.15);
    color: var(--accent-cyan);
  }
}
</style>
