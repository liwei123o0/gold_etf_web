import { ref, onUnmounted } from 'vue'
import { stockService } from '@/services/stockService'
import type { SignalTimeResponse, RealtimeData } from '@/services/stockService'

export function useRealtime(symbol: string, intervalMs: number = 60000) {
  const realtimeData = ref<RealtimeData | null>(null)
  const signalTimeData = ref<SignalTimeResponse | null>(null)
  const isPolling = ref(false)
  let intervalId: number | null = null

  async function fetchRealtime() {
    try {
      const data = await stockService.getRealtime(symbol)
      if (data.code === 0 && data.data[symbol]) {
        realtimeData.value = data.data[symbol]
        await fetchSignalTime(data.data[symbol].price, data.data[symbol].prev_close)
      }
    } catch (e) {
      console.warn('实时数据获取失败:', e)
    }
  }

  async function fetchSignalTime(price: number, prevClose?: number) {
    try {
      const data = await stockService.getSignalTime({
        symbol,
        realtime_price: price,
        prev_close: prevClose
      })
      if (data.code === 0) {
        signalTimeData.value = data
      }
    } catch (e) {
      console.warn('实时信号计算失败:', e)
    }
  }

  function startPolling() {
    fetchRealtime()
    if (intervalMs > 0) {
      intervalId = window.setInterval(fetchRealtime, intervalMs)
      isPolling.value = true
    }
  }

  function stopPolling() {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
      isPolling.value = false
    }
  }

  function setInterval(ms: number) {
    stopPolling()
    if (ms > 0) {
      intervalId = window.setInterval(fetchRealtime, ms)
      isPolling.value = true
    }
  }

  onUnmounted(() => {
    stopPolling()
  })

  return {
    realtimeData,
    signalTimeData,
    isPolling,
    fetchRealtime,
    startPolling,
    stopPolling,
    setInterval
  }
}
