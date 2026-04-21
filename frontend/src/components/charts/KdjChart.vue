<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import type { StockDataResponse } from '@/services/stockService'

const props = defineProps<{
  data?: StockDataResponse
}>()

const chartContainer = ref<HTMLElement | null>(null)
const { initChart, setOption, resize, dispose } = useECharts(chartContainer)

function buildChartOption() {
  if (!props.data) return null

  const { dates, K, D, J } = props.data

  return {
    animation: false,
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const }
    },
    legend: {
      data: ['K', 'D', 'J'],
      top: 10,
      textStyle: { color: '#7986cb' }
    },
    grid: {
      left: '10%',
      right: '10%',
      top: '15%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category' as const,
      data: dates,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#7986cb', show: false }
    },
    yAxis: {
      type: 'value' as const,
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#7986cb' },
      splitLine: { lineStyle: { color: '#222' } }
    },
    dataZoom: [
      { type: 'inside' as const, start: 70, end: 100 }
    ],
    series: [
      {
        name: 'K',
        type: 'line' as const,
        data: K,
        smooth: true,
        lineStyle: { width: 1, color: '#00f2ff' }
      },
      {
        name: 'D',
        type: 'line' as const,
        data: D,
        smooth: true,
        lineStyle: { width: 1, color: '#ff6b9d' }
      },
      {
        name: 'J',
        type: 'line' as const,
        data: J,
        smooth: true,
        lineStyle: { width: 1, color: '#ffd700' }
      },
      {
        name: '参考线',
        type: 'line' as const,
        data: Array(dates.length).fill(80),
        lineStyle: { width: 1, color: 'rgba(239, 83, 80, 0.3)', type: 'dashed' as const }
      },
      {
        name: '参考线2',
        type: 'line' as const,
        data: Array(dates.length).fill(20),
        lineStyle: { width: 1, color: 'rgba(38, 166, 154, 0.3)', type: 'dashed' as const }
      }
    ]
  }
}

watch(() => props.data, () => {
  if (props.data) {
    const option = buildChartOption()
    if (option) setOption(option)
  }
}, { deep: true })

onMounted(() => {
  initChart()
  if (props.data) {
    const option = buildChartOption()
    if (option) setOption(option)
  }
  window.addEventListener('resize', resize)
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
  dispose()
})
</script>

<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<style scoped lang="scss">
.chart-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
}

.chart-container {
  width: 100%;
  height: 200px;
}
</style>
