<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import SimulationStats from '@/components/simulation/SimulationStats.vue'
import SimulationConfig from '@/components/simulation/SimulationConfig.vue'
import PositionList from '@/components/simulation/PositionList.vue'
import SimulationOrderHistory from '@/components/simulation/SimulationOrderHistory.vue'
import AutoTradePanel from '@/components/simulation/AutoTradePanel.vue'
import { useSimulationStore } from '@/stores/simulation'
import { useGlobalSettings } from '@/composables/useGlobalSettings'
import { storeToRefs } from 'pinia'

const simStore = useSimulationStore()
const { portfolio, orders } = storeToRefs(simStore)
const { settings: globalSettings } = useGlobalSettings()

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await simStore.loadPortfolio()
  if (!portfolio.value) {
    await simStore.initPortfolio(100000)
  }
  await simStore.fetchAutoTradeTasks()

  const pollRefresh = async () => {
    await simStore.loadPortfolio()
    await simStore.fetchAutoTradeTasks()
  }

  pollRefresh()
  pollTimer = setInterval(pollRefresh, globalSettings.value.simRealtimeInterval)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="simulation-page">
    <AppHeader />

    <main class="sim-content">
      <SimulationStats />

      <div class="main-grid">
        <SimulationConfig class="order-panel" />
        <PositionList class="position-panel" />
      </div>

      <AutoTradePanel />

      <SimulationOrderHistory v-if="orders.length > 0" :orders="orders" @clear="simStore.clearOrders" />
    </main>
  </div>
</template>

<style scoped lang="scss">
.simulation-page {
  min-height: 100vh;
  background: var(--bg-primary);
}

.sim-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.main-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  align-items: start;

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
}
</style>
