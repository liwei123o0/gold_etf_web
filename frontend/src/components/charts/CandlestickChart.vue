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

  const { dates, kdata, MA5, MA10, MA20, BB_UPPER, BB_LOWER, volume } = props.data

  return {
    animation: false,
    tooltip: {
      show: true,
      trigger: 'item' as const,
      formatter: function(param: any): string {
        const idx = param?.dataIndex
        if (idx == null) return ''
        const date = dates[idx] || ''
        const kd = kdata[idx]
        if (!kd) return ''
        const [open, close, low, high] = kd
        const vol = volume?.[idx] ?? 0
        const change = close - open
        const changePct = open ? ((close - open) / open * 100).toFixed(2) : '0.00'
        const isUp = close >= open
        const color = isUp ? '#ef5350' : '#26a69a'
        return `<div style="font-family:sans-serif;padding:6px 10px;font-size:12px;white-space:nowrap;">
<div style="color:#7986cb;margin-bottom:6px;font-weight:bold;">${date}</div>
<div style="display:grid;grid-template-columns:auto auto;gap:3px 14px;">
<span style="color:#888">开盘</span><span style="color:${color}">${open.toFixed(3)}</span>
<span style="color:#888">收盘</span><span style="color:${color}">${close.toFixed(3)}</span>
<span style="color:#888">最高</span><span style="color:${color}">${high.toFixed(3)}</span>
<span style="color:#888">最低</span><span style="color:${color}">${low.toFixed(3)}</span>
<span style="color:#888">涨跌</span><span style="color:${color}">${change >= 0 ? '+' : ''}${change.toFixed(3)} (${changePct}%)</span>
<span style="color:#888">成交量</span><span style="color:#7986cb">${(vol / 10000).toFixed(2)}万</span>
</div></div>`
      }
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', '布林上轨', '布林下轨'],
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
      axisLabel: { color: '#7986cb' }
    },
    yAxis: {
      type: 'value' as const,
      scale: true,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#7986cb' },
      splitLine: { lineStyle: { color: '#222' } }
    },
    dataZoom: [
      { type: 'inside' as const, start: 70, end: 100 },
      { type: 'slider' as const, start: 70, end: 100 }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick' as const,
        data: kdata.map(d => [d[0], d[1], d[2], d[3]]),
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a'
        }
      },
      {
        name: 'MA5',
        type: 'line' as const,
        data: MA5,
        smooth: true,
        lineStyle: { width: 1, color: '#ff6b9d' }
      },
      {
        name: 'MA10',
        type: 'line' as const,
        data: MA10,
        smooth: true,
        lineStyle: { width: 1, color: '#c2a53a' }
      },
      {
        name: 'MA20',
        type: 'line' as const,
        data: MA20,
        smooth: true,
        lineStyle: { width: 1, color: '#6a5acd' }
      },
      {
        name: '布林上轨',
        type: 'line' as const,
        data: BB_UPPER,
        lineStyle: { width: 1, color: '#667eea', type: 'dashed' as const }
      },
      {
        name: '布林下轨',
        type: 'line' as const,
        data: BB_LOWER,
        lineStyle: { width: 1, color: '#667eea', type: 'dashed' as const }
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
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
  height: 400px;
}
</style>
