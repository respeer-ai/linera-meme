<template>
  <div ref='chartContainer' class='kline-chart' />
</template>

<script setup lang='ts'>
import { ref, watch, onMounted, onBeforeUnmount, defineProps, defineEmits } from 'vue'
import {
  createChart,
  CrosshairMode,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  CandlestickSeries,
  HistogramSeries,
  Time
} from 'lightweight-charts'

interface KLineData {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

const props = defineProps({
  data: { type: Array as () => KLineData[], required: true, default: () => [] },
  pricePrecision: { type: Number, default: 2 },
  volumePrecision: { type: Number, default: 0 }
})

const emit = defineEmits<{(e: 'load-old-data', time: number): void
  (e: 'load-new-data', time: number): void
}>()

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: IChartApi
let candleSeries: ISeriesApi<'Candlestick'>
let volumeSeries: ISeriesApi<'Histogram'>

const initChart = () => {
  if (!chartContainer.value) return

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 500,
    layout: { background: { color: '#131722' }, textColor: '#d9d9d9' },
    grid: {
      vertLines: { color: 'rgba(42,46,57,0.5)' },
      horzLines: { color: 'rgba(42,46,57,0.5)' }
    },
    crosshair: { mode: CrosshairMode.Normal },
    timeScale: { timeVisible: true, secondsVisible: false },
    handleScroll: { mouseWheel: true, pressedMouseMove: true }
  })

  candleSeries = chart.addSeries(CandlestickSeries)
  volumeSeries = chart.addSeries(HistogramSeries)

  chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.7, bottom: 0 } })

  chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRangeChange)
}

const handleVisibleRangeChange = (logicalRange: { from: number; to: number } | null) => {
  if (!logicalRange) return
  if (!props.data.length) return

  const fromIndex = Math.max(Math.floor(logicalRange.from), 0)
  const toIndex = Math.min(Math.ceil(logicalRange.to), props.data.length - 1)

  const firstVisibleTime = props.data[fromIndex].time
  const lastVisibleTime = props.data[toIndex].time

  if (firstVisibleTime <= props.data[0].time) {
    emit('load-old-data', props.data[0].time)
  }
  if (lastVisibleTime >= props.data[props.data.length - 1].time) {
    emit('load-new-data', props.data[props.data.length - 1].time)
  }
}

const updateChartData = () => {
  if (!candleSeries || !volumeSeries) return

  const candleData: CandlestickData[] = props.data.map(d => ({
    time: d.time as Time,
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close
  }))

  const volumeData: HistogramData[] = props.data.map(d => ({
    time: d.time as Time,
    value: d.volume,
    color: d.close >= d.open ? '#26a69a' : '#ef5350'
  }))

  candleSeries.setData(candleData)
  volumeSeries.setData(volumeData)
}

// 响应式更新
watch(() => props.data, updateChartData, { deep: true })
watch(() => props.pricePrecision, () => {
  candleSeries.applyOptions({ priceFormat: { precision: props.pricePrecision, type: 'price', minMove: 1 / Math.pow(10, props.pricePrecision) } })
})
watch(() => props.volumePrecision, () => {
  volumeSeries.applyOptions({ priceFormat: { type: 'volume', precision: props.volumePrecision } })
})

// 生命周期
onMounted(initChart)
onBeforeUnmount(() => {
  chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange)
  chart.remove()
})
</script>

<style scoped>
.kline-chart {
  width: 100%;
  height: 500px;
  background-color: #131722;
}
</style>
