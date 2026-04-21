import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { stockService, type StockDataResponse, type RealtimeData, type NewsItem } from '@/services/stockService'

export const useStockStore = defineStore('stock', () => {
  const currentSymbol = ref('sh518880')
  const symbolName = ref('')
  const startDate = ref<string | null>(null)
  const endDate = ref<string | null>(null)
  const stockData = ref<StockDataResponse | null>(null)
  const realtimeData = ref<RealtimeData | null>(null)
  const news = ref<NewsItem[]>([])
  const loading = ref(false)
  const realtimeInterval = ref(60000)
  const updateTime = ref('')

  const latest = computed(() => stockData.value?.latest)
  const tradeSignal = computed(() => stockData.value?.trade_signal || '观望')
  const gridSignal = computed(() => stockData.value?.grid_signal)
  const signals = computed(() => stockData.value?.signals || [])
  const dates = computed(() => stockData.value?.dates || [])
  const kdata = computed(() => stockData.value?.kdata || [])

  async function loadStockData(symbol: string, start?: string, end?: string) {
    loading.value = true
    try {
      currentSymbol.value = symbol
      startDate.value = start || null
      endDate.value = end || null

      const data = await stockService.getData(symbol, start || undefined, end || undefined)
      stockData.value = data
      symbolName.value = data.symbol_name
      updateTime.value = data.update_time
      return data
    } finally {
      loading.value = false
    }
  }

  async function loadRealtime() {
    try {
      const data = await stockService.getRealtime(currentSymbol.value)
      if (data.code === 0 && data.data[currentSymbol.value]) {
        realtimeData.value = data.data[currentSymbol.value]
      }
    } catch (e) {
      console.warn('实时数据获取失败:', e)
    }
  }

  async function loadNews(symbol?: string) {
    try {
      const data = await stockService.getNews(symbol || currentSymbol.value)
      news.value = data.news
    } catch (e) {
      console.warn('新闻获取失败:', e)
    }
  }

  function setRealtimeInterval(ms: number) {
    realtimeInterval.value = ms
  }

  return {
    currentSymbol,
    symbolName,
    startDate,
    endDate,
    stockData,
    realtimeData,
    news,
    loading,
    realtimeInterval,
    updateTime,
    latest,
    tradeSignal,
    gridSignal,
    signals,
    dates,
    kdata,
    loadStockData,
    loadRealtime,
    loadNews,
    setRealtimeInterval
  }
})
