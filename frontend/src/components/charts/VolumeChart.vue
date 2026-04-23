<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, ColorType, HistogramSeries } from 'lightweight-charts'
import type { ISeriesApi } from 'lightweight-charts'
import type { StockDataResponse } from '@/services/stockService'

const props = defineProps<{
  data?: StockDataResponse
  syncChart?: IChartApi | null
}>()

const container = ref<HTMLElement | null>(null)
let chart: IChartApi | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null

function parseDate(dateStr: string): number {
  return Math.floor(new Date(dateStr).getTime() / 1000)
}

function buildChartData() {
  if (!props.data) return
  const { dates, kdata, volume } = props.data

  volumeSeries?.setData(kdata.map((d, i) => ({
    time: parseDate(dates[i]) as any,
    value: volume[i],
    color: d[1] >= d[0] ? 'rgba(239, 83, 80, 0.5)' : 'rgba(38, 166, 154, 0.5)'
  })))

  chart?.timeScale().fitContent()
}

function initChart() {
  if (!container.value) return

  chart = createChart(container.value, {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#7986cb'
    },
    grid: {
      vertLines: { color: '#222' },
      horzLines: { color: '#222' }
    },
    crosshair: { mode: 1 },
    timeScale: {
      borderColor: '#333',
      timeVisible: false,
      visible: false
    },
    rightPriceScale: { borderColor: '#333' },
    handleScroll: true,
    handleScale: true
  })

  volumeSeries = chart.addSeries(HistogramSeries, {
    priceFormat: { type: 'volume' },
    priceScaleId: 'right'
  })

  chart.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0 } })

  const handleResize = () => {
    if (container.value) chart?.applyOptions({ width: container.value.clientWidth, height: container.value.clientHeight })
  }
  window.addEventListener('resize', handleResize)
  handleResize()
}

onMounted(() => {
  initChart()
  if (props.data) buildChartData()
})

onUnmounted(() => {
  chart?.remove()
  chart = null
})

watch(() => props.data, () => {
  if (props.data && chart) buildChartData()
}, { immediate: true, deep: true })

watch(() => props.syncChart, (syncChart) => {
  if (!syncChart || !chart) return
  syncChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (range) chart?.timeScale().setVisibleLogicalRange(range)
  })
  chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (range) syncChart.timeScale().setVisibleLogicalRange(range)
  })
}, { immediate: true })

defineExpose({ chart: () => chart })
</script>

<template>
  <div class="chart-wrapper">
    <div class="chart-title">成交量</div>
    <div ref="container" class="chart-container"></div>
  </div>
</template>

<style scoped lang="scss">
.chart-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
}
.chart-title {
  color: #7986cb;
  font-size: 13px;
  margin-bottom: 8px;
  font-weight: bold;
}
.chart-container {
  width: 100%;
  height: 140px;
}
</style>
