import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { stockService, type SimulationPortfolio, type SimulationPosition, type SimulationOrder } from '@/services/stockService'
import { useAuthStore } from './auth'

export const useSimulationStore = defineStore('simulation', () => {
  const authStore = useAuthStore()
  
  const portfolio = ref<SimulationPortfolio | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const realtimePrices = ref<Record<string, { price: number; name: string }>>({})

  const account = computed(() => portfolio.value?.account ?? null)
  const positions = computed(() => portfolio.value?.positions ?? [])
  const orders = computed(() => portfolio.value?.orders ?? [])

  async function initPortfolio(initialCapital = 100000) {
    if (!authStore.user) return
    isLoading.value = true
    error.value = null
    try {
      portfolio.value = await stockService.resetSimulation(authStore.user.id, initialCapital)
    } catch (e: any) {
      error.value = e.message
    } finally {
      isLoading.value = false
    }
  }

  async function loadPortfolio() {
    if (!authStore.user) return
    isLoading.value = true
    error.value = null
    try {
      portfolio.value = await stockService.getSimulationPortfolio()
    } catch (e: any) {
      if (e.response?.status !== 404) {
        error.value = e.message
      }
    } finally {
      isLoading.value = false
    }
  }

  async function buy(symbol: string, name: string, price: number, shares: number) {
    if (!authStore.user) return { success: false, error: '未登录' }
    isLoading.value = true
    error.value = null
    try {
      const result = await stockService.placeSimulationOrder(authStore.user.id, 'buy', symbol, name, price, shares)
      if (result.success) {
        portfolio.value = result.portfolio
      } else {
        error.value = result.error
      }
      return result
    } catch (e: any) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      isLoading.value = false
    }
  }

  async function sell(symbol: string, name: string, price: number, shares: number) {
    if (!authStore.user) return { success: false, error: '未登录' }
    isLoading.value = true
    error.value = null
    try {
      const result = await stockService.placeSimulationOrder(authStore.user.id, 'sell', symbol, name, price, shares)
      if (result.success) {
        portfolio.value = result.portfolio
      } else {
        error.value = result.error
      }
      return result
    } catch (e: any) {
      error.value = e.message
      return { success: false, error: e.message }
    } finally {
      isLoading.value = false
    }
  }

  async function closeAll() {
    if (!authStore.user) return
    isLoading.value = true
    error.value = null
    try {
      const result = await stockService.closeAllPositions(authStore.user.id)
      if (result.success) {
        portfolio.value = result.portfolio
      } else {
        error.value = result.error
      }
    } catch (e: any) {
      error.value = e.message
    } finally {
      isLoading.value = false
    }
  }

  async function updateRealtime(symbols: string[]) {
    try {
      const result = await stockService.getRealtime(symbols.join(','))
      const data = result.data
      const priceMap: Record<string, { price: number; name: string }> = {}
      for (const [sym, d] of Object.entries(data)) {
        priceMap[sym] = { price: d.price, name: d.name }
      }
      realtimePrices.value = priceMap
      
      // Update positions current_price and account unrealized_pnl
      if (portfolio.value) {
        let unrealized = 0
        for (const pos of portfolio.value.positions) {
          const rt = priceMap[pos.symbol]
          if (rt) {
            pos.current_price = rt.price
            pos.unrealized_pnl = (rt.price - pos.avg_cost) * pos.shares
            pos.unrealized_pnl_pct = ((rt.price - pos.avg_cost) / pos.avg_cost) * 100
          }
          unrealized += pos.unrealized_pnl
        }
        portfolio.value.account.unrealized_pnl = unrealized
        portfolio.value.account.total_pnl = portfolio.value.account.realized_pnl + unrealized
        portfolio.value.account.market_value = portfolio.value.positions.reduce((sum, p) => sum + p.shares * p.current_price, 0)
        portfolio.value.account.total_assets = portfolio.value.account.cash + portfolio.value.account.market_value
      }
    } catch (e) {
      // silently fail for realtime updates
    }
  }

  return {
    portfolio,
    isLoading,
    error,
    realtimePrices,
    account,
    positions,
    orders,
    initPortfolio,
    loadPortfolio,
    buy,
    sell,
    closeAll,
    updateRealtime
  }
})
