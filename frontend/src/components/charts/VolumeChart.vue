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

  const { dates, kdata, volume } = props.data

  const volumeColors = kdata.map(d => d[1] >= d[0] ? '#ef5350' : '#26a69a')

  return {
    animation: false,
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const }
    },
    legend: {
      data: ['成交量'],
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
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#7986cb' },
      splitLine: { lineStyle: { color: '#222' } }
    },
    dataZoom: [
      { type: 'inside' as const, start: 70, end: 100 }
    ],
    series: [
      {
        name: '成交量',
        type: 'bar' as const,
        data: volume.map((v, i) => ({
          value: v,
          itemStyle: { color: volumeColors[i] }
        }))
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
