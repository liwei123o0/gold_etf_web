<script setup lang="ts">
import { ref, computed } from 'vue'
import { normalizeSymbol, formatDate } from '@/utils/symbol'

const emit = defineEmits<{
  search: [symbol: string, startDate: string | null, endDate: string | null]
  intervalChange: [ms: number]
}>()

const stockCode = ref('')
const startDate = ref('')
const endDate = ref('')
const selectedInterval = ref(60000)
const activeQuickBtn = ref(3)

const intervals = [
  { label: '15秒', value: 15000 },
  { label: '30秒', value: 30000 },
  { label: '1分钟', value: 60000 },
  { label: '手动', value: 0 }
]

function setDateRange(months: number) {
  activeQuickBtn.value = months
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - months)
  startDate.value = formatDate(start)
  endDate.value = formatDate(end)
  doSearch()
}

function doSearch() {
  const symbol = normalizeSymbol(stockCode.value || 'sh518880')
  emit('search', symbol, startDate.value || null, endDate.value || null)
}

function onIntervalChange() {
  emit('intervalChange', selectedInterval.value)
}

// Initialize with 3 months
setDateRange(3)
</script>

<template>
  <div class="search-section">
    <form class="search-form" @submit.prevent="doSearch">
      <div class="form-row">
        <label class="form-label">股票代码</label>
        <input
          v-model="stockCode"
          type="text"
          class="stock-input"
          placeholder="如 518880、000300"
          autocomplete="off"
        />
      </div>

      <div class="form-row">
        <label class="form-label">开始日期</label>
        <input v-model="startDate" type="date" class="date-input" />
      </div>

      <div class="form-row">
        <label class="form-label">结束日期</label>
        <input v-model="endDate" type="date" class="date-input" />
      </div>

      <button type="submit" class="search-btn">分析</button>
    </form>

    <div class="quick-dates">
      <span class="quick-label">快捷范围：</span>
      <button
        v-for="btn in [1, 3, 6, 12, 24]"
        :key="btn"
        class="quick-btn"
        :class="{ active: activeQuickBtn === btn }"
        @click="setDateRange(btn)"
      >
        {{ btn === 1 ? '近1月' : btn === 12 ? '近1年' : `近${btn}月` }}
      </button>
    </div>

    <div class="realtime-options">
      <span class="quick-label">刷新频率：</span>
      <select v-model="selectedInterval" class="interval-select" @change="onIntervalChange">
        <option v-for="opt in intervals" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
    </div>
  </div>
</template>

<style scoped lang="scss">
.search-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.stock-input,
.date-input {
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s;

  &:focus {
    border-color: var(--accent-purple);
  }

  &::placeholder {
    color: var(--text-muted);
  }
}

.stock-input {
  min-width: 140px;
}

.date-input {
  min-width: 130px;
  color-scheme: dark;
}

.search-btn {
  padding: 10px 24px;
  background: linear-gradient(135deg, var(--accent-purple) 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.85;
  }
}

.quick-dates,
.realtime-options {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 12px;
  color: var(--text-muted);
}

.quick-btn {
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover,
  &.active {
    border-color: var(--accent-purple);
    color: var(--accent-purple);
  }
}

.interval-select {
  padding: 4px 28px 4px 10px;
  background: rgba(20, 25, 45, 0.95);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 12px;
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
</style>
