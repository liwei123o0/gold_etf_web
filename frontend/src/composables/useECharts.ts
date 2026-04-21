import { ref, onMounted, onUnmounted, type Ref } from 'vue'
import * as echarts from 'echarts'

export function useECharts(containerRef: Ref<HTMLElement | null>) {
  const chartInstance = ref<echarts.ECharts | null>(null)

  function initChart() {
    if (!containerRef.value) return null
    chartInstance.value = echarts.init(containerRef.value)
    return chartInstance.value
  }

  function setOption(option: echarts.EChartsOption) {
    chartInstance.value?.setOption(option)
  }

  function resize() {
    chartInstance.value?.resize()
  }

  function dispose() {
    chartInstance.value?.dispose()
    chartInstance.value = null
  }

  onUnmounted(() => {
    dispose()
  })

  return {
    chartInstance,
    initChart,
    setOption,
    resize,
    dispose
  }
}

export { echarts }
