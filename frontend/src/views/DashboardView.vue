<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import type { IChartApi } from 'lightweight-charts'
import { useAuth } from '@/composables/useAuth'
import { useStockStore } from '@/stores/stock'
import { useGlobalSettings } from '@/composables/useGlobalSettings'
import { stockService } from '@/services/stockService'
import AppHeader from '@/components/layout/AppHeader.vue'
import SearchSection from '@/components/search/SearchSection.vue'
import SignalBar from '@/components/trading/SignalBar.vue'
import GridCard from '@/components/trading/GridCard.vue'
import SummaryCards from '@/components/trading/SummaryCards.vue'
import SignalGrid from '@/components/trading/SignalGrid.vue'
import SimulationCard from '@/components/trading/SimulationCard.vue'
import CandlestickChart from '@/components/charts/CandlestickChart.vue'
import MacdChart from '@/components/charts/MacdChart.vue'
import KdjChart from '@/components/charts/KdjChart.vue'
import VolumeChart from '@/components/charts/VolumeChart.vue'
import NewsSection from '@/components/news/NewsSection.vue'

const { user } = useAuth()
const stockStore = useStockStore()
const { settings: globalSettings, updateSetting } = useGlobalSettings()

const selectedMa = ref('MA20')
const realtimeInterval = computed(() => globalSettings.value.realtimeInterval)
let realtimeTimer: number | null = null
const mainChartRef = ref<{ chart: () => IChartApi | null } | null>(null)

const realtimeData = computed(() => stockStore.realtimeData)
const changePct = computed(() => realtimeData.value?.change_pct)
const isGoldETF = computed(() => stockStore.currentSymbol.replace(/sh|sz|bj/g, '') === '518880')
const stockDataForCharts = computed(() => stockStore.stockData ?? undefined)

async function handleSearch(symbol: string, startDate: string | null, endDate: string | null) {
  await stockStore.loadStockData(symbol, startDate || undefined, endDate || undefined)
  await stockStore.loadNews(symbol)
  startRealtimePolling()
}

async function loadRealtime() {
  if (stockStore.currentSymbol) {
    await stockStore.loadRealtime()
  }
}

function startRealtimePolling() {
  stopRealtimePolling()
  if (realtimeInterval.value > 0) {
    loadRealtime()
    realtimeTimer = window.setInterval(loadRealtime, realtimeInterval.value)
  }
}

function stopRealtimePolling() {
  if (realtimeTimer) {
    clearInterval(realtimeTimer)
    realtimeTimer = null
  }
}

function onMaChange(maKey: string) {
  selectedMa.value = maKey
}

onMounted(async () => {
  // Load initial data
  await stockStore.loadStockData('sh518880')
  await stockStore.loadNews('sh518880')
  startRealtimePolling()
})

onUnmounted(() => {
  stopRealtimePolling()
})
</script>

<template>
  <div class="dashboard">
    <AppHeader />

    <main class="main-content">
      <SearchSection
        @search="handleSearch"
      />

      <SignalBar
        :trade-signal="stockStore.tradeSignal"
        :latest="stockStore.latest"
        :grid-signal="stockStore.gridSignal"
        :realtime-price="realtimeData?.price"
        :change-pct="changePct"
      />

      <GridCard
        :grid-signal="stockStore.stockData?.grid_signals?.[selectedMa] || stockStore.gridSignal"
        :selected-ma="selectedMa"
        @ma-change="onMaChange"
      />

      <SummaryCards
        :latest="stockStore.latest"
        :realtime-price="realtimeData?.price"
        :change-pct="changePct"
      />

      <SignalGrid
        :signals="stockStore.signals"
        :trade-signal="stockStore.tradeSignal"
        :grid-signal="stockStore.gridSignal"
      />

      <SimulationCard
        :symbol="stockStore.currentSymbol"
        :start-date="stockStore.startDate"
        :end-date="stockStore.endDate"
      />

      <CandlestickChart ref="mainChartRef" :data="stockDataForCharts" :realtime="stockStore.realtimeData" />

      <div class="charts-grid">
        <MacdChart :data="stockDataForCharts" :sync-chart="mainChartRef?.chart() ?? null" :realtime="stockStore.realtimeData" />
        <KdjChart :data="stockDataForCharts" :sync-chart="mainChartRef?.chart() ?? null" :realtime="stockStore.realtimeData" />
        <VolumeChart :data="stockDataForCharts" :sync-chart="mainChartRef?.chart() ?? null" :realtime="stockStore.realtimeData" />
      </div>

      <NewsSection
        :news="stockStore.news"
        :title="isGoldETF ? '📰 黄金国际新闻' : '📰 相关新闻'"
      />

      <div class="risk-warning">
        <h4>⚠️ 风险提示</h4>
        <p>本系统仅供技术分析参考，不构成任何投资建议。黄金ETF投资有风险，入市需谨慎。请根据自身风险承受能力做出投资决策，过往业绩不代表未来表现。</p>
      </div>

      <footer class="footer">
        数据来源: 新浪财经 · 更新于 {{ stockStore.updateTime || '-' }} · 仅供技术分析参考
      </footer>
    </main>
  </div>
</template>

<style scoped lang="scss">
.dashboard {
  min-height: 100vh;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
  overflow-y: auto;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.risk-warning {
  margin-top: 20px;
  padding: 16px;
  background: rgba(255, 152, 0, 0.08);
  border: 1px solid rgba(255, 152, 0, 0.2);
  border-radius: 12px;

  h4 {
    color: #FF9800;
    font-size: 14px;
    margin-bottom: 8px;
  }

  p {
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.6;
  }
}

.footer {
  margin-top: 20px;
  padding: 16px 0;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  border-top: 1px solid var(--border-color);
}
</style>
