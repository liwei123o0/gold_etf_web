<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useECharts } from '@/composables/useECharts'
import type { EquityPoint } from '@/services/stockService'

const props = defineProps<{
  data?: EquityPoint[]
  title?: string
}>()

const chartContainer = ref<HTMLElement | null>(null)
const { initChart, setOption, resize, dispose } = useECharts(chartContainer)

function buildChartOption() {
  if (!props.data || props.data.length === 0) return null

  const dates = props.data.map(d => d.date)
  const equities = props.data.map(d => d.equity)

  // Calculate min/max for better visualization
  const minEquity = Math.min(...equities)
  const maxEquity = Math.max(...equities)
  const padding = (maxEquity - minEquity) * 0.1

  return {
    animation: false,
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const },
      formatter: (params: any) => {
        const p = params[0]
        return `${p.axisValue}<br/>资金: <strong>${p.value.toFixed(2)}</strong>`
      }
    },
    title: {
      text: props.title || '资金曲线',
      left: 'center',
      textStyle: {
        color: '#7986cb',
        fontSize: 14
      }
    },
    grid: {
      left: '15%',
      right: '5%',
      top: '25%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category' as const,
      data: dates,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#7986cb', fontSize: 10 }
    },
    yAxis: {
      type: 'value' as const,
      min: minEquity - padding,
      max: maxEquity + padding,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: {
        color: '#7986cb',
        formatter: (v: number) => (v / 10000).toFixed(1) + '万'
      },
      splitLine: { lineStyle: { color: '#222' } }
    },
    dataZoom: [
      { type: 'inside' as const, start: 0, end: 100 }
    ],
    series: [
      {
        name: '资金',
        type: 'line' as const,
        data: equities,
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#667eea'
        },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
              { offset: 1, color: 'rgba(102, 126, 234, 0.05)' }
            ]
          }
        },
        itemStyle: {
          color: '#667eea'
        }
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
  <div class="equity-chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<style scoped lang="scss">
.equity-chart-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
  height: 250px;
}
</style>