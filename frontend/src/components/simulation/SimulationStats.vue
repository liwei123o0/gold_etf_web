<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { storeToRefs } from 'pinia'

const simStore = useSimulationStore()
const { portfolio } = storeToRefs(simStore)

const account = computed(() => portfolio.value?.account ?? null)
const returnColor = computed(() => {
  if (!account.value) return '#7986cb'
  return account.value.total_pnl >= 0 ? '#26a69a' : '#ef5350'
})
const returnSign = computed(() => {
  if (!account.value) return ''
  return account.value.total_pnl >= 0 ? '+' : ''
})

// 初始资金设置
const showResetForm = ref(false)
const resetCapital = ref(100000)
const isResetting = ref(false)

async function handleReset() {
  if (resetCapital.value < 1000) return
  isResetting.value = true
  try {
    await simStore.initPortfolio(resetCapital.value)
    showResetForm.value = false
  } finally {
    isResetting.value = false
  }
}
</script>

<template>
  <div class="sim-stats">
    <div class="stat-card">
      <span class="stat-label">初始资金</span>
      <span class="stat-value">{{ account ? (account.initial_capital / 10000).toFixed(2) : '--' }}万</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">当前权益</span>
      <span class="stat-value">{{ account ? (account.total_assets / 10000).toFixed(2) : '--' }}万</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">总盈亏</span>
      <span class="stat-value" :style="{ color: returnColor }">
        {{ returnSign }}{{ account ? (account.total_pnl).toFixed(2) : '--' }}元
      </span>
    </div>
    <div class="stat-card">
      <span class="stat-label">可用资金</span>
      <span class="stat-value">{{ account ? account.cash.toFixed(2) : '--' }}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">持仓市值</span>
      <span class="stat-value">{{ account ? account.market_value.toFixed(2) : '--' }}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">浮动盈亏</span>
      <span class="stat-value" :style="{ color: account && account.unrealized_pnl >= 0 ? '#26a69a' : '#ef5350' }">
        {{ account ? (account.unrealized_pnl >= 0 ? '+' : '') + account.unrealized_pnl.toFixed(2) : '--' }}
      </span>
    </div>
    <div class="stat-card">
      <span class="stat-label">已实现盈亏</span>
      <span class="stat-value" :style="{ color: account && account.realized_pnl >= 0 ? '#26a69a' : '#ef5350' }">
        {{ account ? (account.realized_pnl >= 0 ? '+' : '') + account.realized_pnl.toFixed(2) : '--' }}
      </span>
    </div>
    <div class="stat-card">
      <span class="stat-label">持仓笔数</span>
      <span class="stat-value">{{ portfolio?.positions?.length ?? 0 }}</span>
    </div>

    <!-- 重置资金 -->
    <div class="stat-card reset-card">
      <template v-if="!showResetForm">
        <span class="stat-label">重置账户</span>
        <button class="reset-btn" @click="showResetForm = true">设置初始资金</button>
      </template>
      <template v-else>
        <div class="reset-form">
          <input 
            v-model.number="resetCapital" 
            type="number" 
            min="1000" 
            step="10000"
            class="reset-input"
            placeholder="输入初始资金"
          />
          <div class="reset-actions">
            <button class="confirm-btn" :disabled="isResetting || resetCapital < 1000" @click="handleReset">
              {{ isResetting ? '重置中...' : '确认' }}
            </button>
            <button class="cancel-btn" @click="showResetForm = false; resetCapital = 100000">取消</button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.sim-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;

  @media (max-width: 900px) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-label {
  color: #7986cb;
  font-size: 12px;
}

.stat-value {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: bold;
}

.reset-card {
  justify-content: center;
}

.reset-btn {
  padding: 6px 12px;
  background: rgba(0, 242, 255, 0.1);
  border: 1px solid var(--accent-cyan);
  border-radius: 6px;
  color: var(--accent-cyan);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 242, 255, 0.2);
  }
}

.reset-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reset-input {
  padding: 6px 10px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  width: 100%;

  &:focus {
    outline: none;
    border-color: var(--accent-cyan);
  }
}

.reset-actions {
  display: flex;
  gap: 6px;
}

.confirm-btn {
  flex: 1;
  padding: 5px 8px;
  background: var(--accent-cyan);
  border: none;
  border-radius: 4px;
  color: #000;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;

  &:hover:not(:disabled) { opacity: 0.85; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.cancel-btn {
  padding: 5px 8px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;

  &:hover { border-color: var(--text-secondary); }
}
</style>
