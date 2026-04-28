<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useSimulationStore } from '@/stores/simulation'
import { useStockStore } from '@/stores/stock'
import { storeToRefs } from 'pinia'

const simStore = useSimulationStore()
const stockStore = useStockStore()
const { realtimePrices } = storeToRefs(simStore)

const symbol = ref('sh518880')
const direction = ref<'buy' | 'sell'>('buy')
const shares = ref(100)
const priceMode = ref<'realtime' | 'custom'>('realtime')
const customPrice = ref<number>(0)

const currentRealtime = computed(() => realtimePrices.value[symbol.value])
const realtimePrice = computed(() => currentRealtime.value?.price ?? 0)
const displayPrice = computed(() => {
  if (priceMode.value === 'custom') return customPrice.value > 0 ? customPrice.value.toFixed(3) : '--'
  return realtimePrice.value > 0 ? realtimePrice.value.toFixed(3) : '--'
})
const effectivePrice = computed(() => {
  if (priceMode.value === 'custom') return customPrice.value
  return realtimePrice.value
})
const orderAmount = computed(() => effectivePrice.value * shares.value)

// Load realtime when symbol changes
watch(() => symbol.value, async (sym) => {
  if (sym) {
    await stockStore.loadRealtime(sym)
  }
}, { immediate: true })

async function submitOrder() {
  if (!simStore.portfolio) return
  const price = effectivePrice.value
  if (price <= 0) return
  const name = currentRealtime.value?.name || symbol.value

  if (direction.value === 'buy') {
    await simStore.buy(symbol.value, name, price, shares.value)
  } else {
    await simStore.sell(symbol.value, name, price, shares.value)
  }
}

const canSubmit = computed(() => {
  return effectivePrice.value > 0 && shares.value > 0 && !simStore.isLoading
})
</script>

<template>
  <div class="sim-config">
    <h3 class="panel-title">下单交易</h3>

    <div class="order-form">
      <div class="form-row">
        <label>证券代码</label>
        <input v-model="symbol" type="text" class="input" placeholder="如 sh518880" />
      </div>

      <div class="form-row">
        <label>方向</label>
        <div class="direction-btns">
          <button
            :class="['dir-btn', 'buy-btn', { active: direction === 'buy' }]"
            @click="direction = 'buy'"
          >买入</button>
          <button
            :class="['dir-btn', 'sell-btn', { active: direction === 'sell' }]"
            @click="direction = 'sell'"
          >卖出</button>
        </div>
      </div>

      <!-- 价格选择 -->
      <div class="form-row">
        <label>价格方式</label>
        <div class="price-mode-btns">
          <button
            :class="['mode-btn', { active: priceMode === 'realtime' }]"
            @click="priceMode = 'realtime'"
          >实时价</button>
          <button
            :class="['mode-btn', { active: priceMode === 'custom' }]"
            @click="priceMode = 'custom'"
          >自定义</button>
        </div>
      </div>

      <div class="form-row">
        <label>{{ priceMode === 'realtime' ? '实时价格' : '自定义价格' }}</label>
        <template v-if="priceMode === 'realtime'">
          <span class="price-display" :style="{ color: direction === 'buy' ? '#ef5350' : '#26a69a' }">
            {{ displayPrice }}
          </span>
          <span class="hint">参考实时行情</span>
        </template>
        <template v-else>
          <input
            v-model.number="customPrice"
            type="number"
            min="0.001"
            step="0.001"
            class="input price-input"
            placeholder="输入价格"
          />
        </template>
      </div>

      <div class="form-row">
        <label>数量（手）</label>
        <input v-model.number="shares" type="number" min="100" step="100" class="input" />
        <span class="hint">每手=100股</span>
      </div>

      <div class="order-preview">
        <span class="preview-label">预计{{ direction === 'buy' ? '支出' : '收入' }}</span>
        <span class="preview-value" :style="{ color: direction === 'buy' ? '#ef5350' : '#26a69a' }">
          {{ orderAmount > 0 ? orderAmount.toFixed(2) : '--' }} 元
        </span>
      </div>

      <button
        class="submit-btn"
        :class="direction === 'buy' ? 'buy-submit' : 'sell-submit'"
        :disabled="!canSubmit"
        @click="submitOrder"
      >
        {{ direction === 'buy' ? '买入' : '卖出' }} {{ symbol }}
      </button>

      <div v-if="simStore.error" class="error-msg">{{ simStore.error }}</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.sim-config {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}

.panel-title {
  color: #7986cb;
  font-size: 15px;
  margin: 0 0 16px;
}

.order-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;

  label {
    width: 80px;
    color: var(--text-secondary);
    font-size: 13px;
    flex-shrink: 0;
  }
}

.input {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;

  &:focus {
    outline: none;
    border-color: var(--accent-cyan);
  }
}

.price-input {
  flex: 1;
  max-width: 140px;
}

.direction-btns {
  display: flex;
  gap: 8px;
}

.dir-btn {
  padding: 6px 20px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &.buy-btn.active {
    background: rgba(239, 83, 80, 0.15);
    border-color: #ef5350;
    color: #ef5350;
  }

  &.sell-btn.active {
    background: rgba(38, 166, 154, 0.15);
    border-color: #26a69a;
    color: #26a69a;
  }
}

.price-mode-btns {
  display: flex;
  gap: 6px;
}

.mode-btn {
  padding: 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &.active {
    background: rgba(0, 242, 255, 0.12);
    border-color: var(--accent-cyan);
    color: var(--accent-cyan);
  }
}

.price-display {
  font-size: 18px;
  font-weight: bold;
  font-family: monospace;
}

.hint {
  color: var(--text-muted);
  font-size: 12px;
}

.order-preview {
  padding: 12px;
  background: var(--bg-hover);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-label {
  color: var(--text-secondary);
  font-size: 13px;
}

.preview-value {
  font-size: 16px;
  font-weight: bold;
  font-family: monospace;
}

.submit-btn {
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 4px;

  &.buy-submit {
    background: linear-gradient(135deg, #ef5350, #c62828);
    color: white;

    &:hover:not(:disabled) { opacity: 0.9; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }

  &.sell-submit {
    background: linear-gradient(135deg, #26a69a, #00695c);
    color: white;

    &:hover:not(:disabled) { opacity: 0.9; }
    &:disabled { opacity: 0.5; cursor: not-allowed; }
  }
}

.error-msg {
  color: #ef5350;
  font-size: 13px;
  text-align: center;
}
</style>
