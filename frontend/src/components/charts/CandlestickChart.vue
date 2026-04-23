<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, ColorType, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts'
import type { ISeriesApi } from 'lightweight-charts'
import type { StockDataResponse } from '@/services/stockService'

const props = defineProps<{
  data?: StockDataResponse
  realtime?: {
    price: number
    open: number
    high: number
    low: number
    change: number
    change_pct: number
    prev_close: number
    date: string
    time: string
  } | null
}>()

const topContainer = ref<HTMLElement | null>(null)
const bottomContainer = ref<HTMLElement | null>(null)
const tooltipEl = ref<HTMLElement | null>(null)

let topChart: IChartApi | null = null
let bottomChart: IChartApi | null = null

let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let ma5Series: ISeriesApi<'Line'> | null = null
let ma10Series: ISeriesApi<'Line'> | null = null
let ma20Series: ISeriesApi<'Line'> | null = null
let bbUpperSeries: ISeriesApi<'Line'> | null = null
let bbLowerSeries: ISeriesApi<'Line'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null

function parseDate(dateStr: string): number {
  const d = new Date(dateStr)
  return Math.floor(d.getTime() / 1000)
}

function formatNum(n: number, decimals = 3): string {
  return n.toFixed(decimals)
}

function syncTimeScale(source: IChartApi, target: IChartApi) {
  source.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (range) target.timeScale().setVisibleLogicalRange(range)
  })
  target.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (range) source.timeScale().setVisibleLogicalRange(range)
  })
}

function buildChartData() {
  if (!props.data) return

  const { dates, kdata, MA5, MA10, MA20, BB_UPPER, BB_LOWER, volume } = props.data

  const candleData = kdata.map((d, i) => {
    const open = d[0]
    const close = d[1]
    const low = d[2]
    const high = d[3]
    const isUp = close >= open
    return {
      time: parseDate(dates[i]) as any,
      open,
      high,
      low,
      close,
      color: isUp ? '#ef5350' : '#26a69a',
      borderColor: isUp ? '#ef5350' : '#26a69a',
      wickColor: isUp ? '#ef5350' : '#26a69a'
    }
  })

  const volumeData = kdata.map((d, i) => ({
    time: parseDate(dates[i]) as any,
    value: volume[i],
    color: d[1] >= d[0] ? 'rgba(239, 83, 80, 0.5)' : 'rgba(38, 166, 154, 0.5)'
  }))

  candlestickSeries?.setData(candleData)
  ma5Series?.setData(MA5.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  ma10Series?.setData(MA10.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  ma20Series?.setData(MA20.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  bbUpperSeries?.setData(BB_UPPER.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  bbLowerSeries?.setData(BB_LOWER.map((v, i) => ({ time: parseDate(dates[i]) as any, value: v })))
  volumeSeries?.setData(volumeData)

  topChart?.timeScale().fitContent()
}

function initTopChart() {
  if (!topContainer.value) return

  topChart = createChart(topContainer.value, {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#7986cb'
    },
    grid: {
      vertLines: { color: '#222' },
      horzLines: { color: '#222' }
    },
    crosshair: {
      mode: 1,
      vertLine: {
        color: 'rgba(121, 134, 203, 0.5)',
        width: 1,
        style: 2,
        labelBackgroundColor: '#7986cb'
      },
      horzLine: {
        color: 'rgba(121, 134, 203, 0.5)',
        width: 1,
        style: 2,
        labelBackgroundColor: '#7986cb'
      }
    },
    timeScale: {
      borderColor: '#333',
      timeVisible: false
    },
    rightPriceScale: {
      borderColor: '#333'
    },
    handleScroll: true,
    handleScale: true
  })

  candlestickSeries = topChart.addSeries(CandlestickSeries, {
    upColor: '#ef5350',
    downColor: '#26a69a',
    borderUpColor: '#ef5350',
    borderDownColor: '#26a69a',
    wickUpColor: '#ef5350',
    wickDownColor: '#26a69a'
  })

  ma5Series = topChart.addSeries(LineSeries, {
    color: '#ff6b9d',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false
  })

  ma10Series = topChart.addSeries(LineSeries, {
    color: '#c2a53a',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false
  })

  ma20Series = topChart.addSeries(LineSeries, {
    color: '#6a5acd',
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: false
  })

  bbUpperSeries = topChart.addSeries(LineSeries, {
    color: '#667eea',
    lineWidth: 1,
    lineStyle: 2,
    priceLineVisible: false,
    lastValueVisible: false
  })

  bbLowerSeries = topChart.addSeries(LineSeries, {
    color: '#667eea',
    lineWidth: 1,
    lineStyle: 2,
    priceLineVisible: false,
    lastValueVisible: false
  })

  // 十字光标移动时更新 tooltip
  topChart.subscribeCrosshairMove((param) => {
    if (!tooltipEl.value) return

    if (!param.time || !param.seriesData || !props.data) {
      tooltipEl.value.style.opacity = '0'
      return
    }

    const candleData = param.seriesData.get(candlestickSeries!) as any
    if (!candleData) {
      tooltipEl.value.style.opacity = '0'
      return
    }

    const { open, high, low, close } = candleData
    const isUp = close >= open
    const change = close - open
    const changePct = open ? ((close - open) / open * 100).toFixed(2) : '0.00'
    const color = isUp ? '#ef5350' : '#26a69a'

    // 找到对应的成交量
    const dates = props.data.dates
    const volume = props.data.volume
    const idx = dates.findIndex(d => parseDate(d) === (param.time as number))
    const vol = idx >= 0 ? volume[idx] : 0

    // 格式化日期
    const date = new Date((param.time as number) * 1000)
    const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

    tooltipEl.value.innerHTML = `
      <div style="color:#7986cb;font-weight:bold;margin-bottom:6px;">${dateStr}</div>
      <div style="display:grid;grid-template-columns:auto auto;gap:2px 16px;font-size:12px;">
        <span style="color:#888">开盘</span><span style="color:${color}">${formatNum(open)}</span>
        <span style="color:#888">收盘</span><span style="color:${color}">${formatNum(close)}</span>
        <span style="color:#888">最高</span><span style="color:${color}">${formatNum(high)}</span>
        <span style="color:#888">最低</span><span style="color:${color}">${formatNum(low)}</span>
        <span style="color:#888">涨跌</span><span style="color:${color}">${change >= 0 ? '+' : ''}${formatNum(change)} (${changePct}%)</span>
        <span style="color:#888">成交量</span><span style="color:#7986cb">${(vol / 10000).toFixed(2)}万</span>
      </div>
    `
    tooltipEl.value.style.opacity = '1'
  })
}

function initBottomChart() {
  if (!bottomContainer.value) return

  bottomChart = createChart(bottomContainer.value, {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: '#7986cb'
    },
    grid: {
      vertLines: { color: '#222' },
      horzLines: { color: '#222' }
    },
    crosshair: {
      mode: 1
    },
    timeScale: {
      borderColor: '#333',
      timeVisible: false,
      visible: false
    },
    rightPriceScale: {
      borderColor: '#333'
    },
    handleScroll: true,
    handleScale: true
  })

  volumeSeries = bottomChart.addSeries(HistogramSeries, {
    priceFormat: { type: 'volume' },
    priceScaleId: 'right'
  })

  bottomChart.priceScale('right').applyOptions({
    scaleMargins: { top: 0.1, bottom: 0 }
  })
}

function handleResize() {
  if (topContainer.value) {
    topChart?.applyOptions({
      width: topContainer.value.clientWidth,
      height: topContainer.value.clientHeight
    })
  }
  if (bottomContainer.value) {
    bottomChart?.applyOptions({
      width: bottomContainer.value.clientWidth,
      height: bottomContainer.value.clientHeight
    })
  }
}

onMounted(() => {
  initTopChart()
  initBottomChart()

  if (topChart && bottomChart) {
    syncTimeScale(topChart, bottomChart)
  }

  if (props.data) {
    buildChartData()
  }

  window.addEventListener('resize', handleResize)
  handleResize()
})

onUnmounted(() => {
  topChart?.remove()
  bottomChart?.remove()
  topChart = null
  bottomChart = null
})

watch(() => props.data, () => {
  if (props.data && topChart && bottomChart) {
    buildChartData()
  }
}, { deep: true })

watch(() => props.realtime, () => {
  if (!props.realtime || !candlestickSeries || !props.data) return
  const { price, open, high, low, prev_close } = props.realtime
  const dates = props.data.dates
  const lastDate = dates[dates.length - 1]
  const today = new Date().toISOString().split('T')[0]

  if (lastDate !== today) {
    // 今天没有数据，创建一个新 K 线
    const newBar = {
      time: parseDate(today) as any,
      open,
      high,
      low,
      close: price,
      color: price >= prev_close ? '#ef5350' : '#26a69a',
      borderColor: price >= prev_close ? '#ef5350' : '#26a69a',
      wickColor: price >= prev_close ? '#ef5350' : '#26a69a'
    }
    candlestickSeries.update(newBar)
  } else {
    // 更新当天最后一根 K 线
    const isUp = price >= prev_close
    candlestickSeries.update({
      time: parseDate(lastDate) as any,
      open,
      high: Math.max(high, price),
      low: Math.min(low, price),
      close: price,
      color: isUp ? '#ef5350' : '#26a69a',
      borderColor: isUp ? '#ef5350' : '#26a69a',
      wickColor: isUp ? '#ef5350' : '#26a69a'
    })
  }

  // 更新成交量
  if (volumeSeries && props.realtime.volume) {
    const vol = props.realtime.volume
    volumeSeries.update({
      time: parseDate(lastDate === today ? lastDate : today) as any,
      value: vol,
      color: price >= prev_close ? 'rgba(239, 83, 80, 0.5)' : 'rgba(38, 166, 154, 0.5)'
    })
  }
}, { deep: true })

defineExpose({ chart: () => topChart })
</script>

<template>
  <div class="chart-wrapper">
    <div ref="topContainer" class="chart-container top">
      <div ref="tooltipEl" class="chart-tooltip"></div>
    </div>
    <div ref="bottomContainer" class="chart-container bottom"></div>
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
  position: relative;
}

.top {
  height: 320px;
  border-bottom: 1px solid var(--border-color);
}

.bottom {
  height: 120px;
}

.chart-tooltip {
  position: absolute;
  top: 10px;
  left: 60px;
  background: rgba(20, 20, 30, 0.95);
  border: 1px solid #333;
  border-radius: 8px;
  padding: 10px 14px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 10;
  font-family: sans-serif;
}
</style>
