<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, ColorType, LineSeries } from 'lightweight-charts'
import type { ISeriesApi } from 'lightweight-charts'
import type { StockDataResponse } from '@/services/stockService'

const props = defineProps<{
  data?: StockDataResponse
  syncChart?: IChartApi | null
}>()

const container = ref<HTMLElement | null>(null)
let chart: IChartApi | null = null
let kSeries: ISeriesApi<'Line'> | null = null
let dSeries: ISeriesApi<'Line'> | null = null
let jSeries: ISeriesApi<'Line'> | null = null
let line80: ISeriesApi<'Line'> | null = null
let line20: ISeriesApi<'Line'> | null = null

function parseDate(dateStr: string): number {
  return Math.floor(new Date(dateStr).getTime() / 1000)
}

function buildChartData() {
  if (!props.data) return
  const { dates, K, D, J } = props.data

  kSeries?.setData(K.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  dSeries?.setData(D.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  jSeries?.setData(J.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  line80?.setData(dates.map((d, i) => ({ time: parseDate(d) as any, value: 80 })))
  line20?.setData(dates.map((d, i) => ({ time: parseDate(d) as any, value: 20 })))

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
      timeVisible: false
    },
    rightPriceScale: { borderColor: '#333' },
    handleScroll: true,
    handleScale: true
  })

  kSeries = chart.addSeries(LineSeries, {
    color: '#00f2ff',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false
  })

  dSeries = chart.addSeries(LineSeries, {
    color: '#ff6b9d',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false
  })

  jSeries = chart.addSeries(LineSeries, {
    color: '#ffd700',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false
  })

  line80 = chart.addSeries(LineSeries, {
    color: 'rgba(239, 83, 80, 0.3)',
    lineWidth: 1,
    lineStyle: 2,
    priceLineVisible: false,
    lastValueVisible: false
  })

  line20 = chart.addSeries(LineSeries, {
    color: 'rgba(38, 166, 154, 0.3)',
    lineWidth: 1,
    lineStyle: 2,
    priceLineVisible: false,
    lastValueVisible: false
  })

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
    <div class="chart-title">KDJ</div>
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
  height: 180px;
}
</style>
