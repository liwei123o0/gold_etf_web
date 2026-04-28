<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import SimulationStats from '@/components/simulation/SimulationStats.vue'
import SimulationConfig from '@/components/simulation/SimulationConfig.vue'
import PositionList from '@/components/simulation/PositionList.vue'
import SimulationOrderHistory from '@/components/simulation/SimulationOrderHistory.vue'
import { useSimulationStore } from '@/stores/simulation'
import { storeToRefs } from 'pinia'

const simStore = useSimulationStore()
const { orders, portfolio } = storeToRefs(simStore)

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await simStore.loadPortfolio()
  if (!portfolio.value) {
    await simStore.initPortfolio(100000)
  }
  
  const pollRealtime = async () => {
    const pos = simStore.positions
    if (pos.length > 0) {
      const symbols = pos.map((p: any) => p.symbol)
      await simStore.updateRealtime(symbols)
    }
  }
  
  pollRealtime()
  pollTimer = setInterval(pollRealtime, 5000)
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

      <SimulationOrderHistory v-if="orders.length > 0" :orders="orders" />
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
