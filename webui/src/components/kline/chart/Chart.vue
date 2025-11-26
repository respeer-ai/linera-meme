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
  Time,
  LineSeries,
  LineData
} from 'lightweight-charts'
import { KLineData } from './KlineData'

const props = defineProps({
  data: { type: Array as () => KLineData[], required: true, default: () => [] },
  pricePrecision: { type: Number, default: 10 },
  volumePrecision: { type: Number, default: 4 }
})

const emit = defineEmits<{(e: 'load-old-data', time: number): void
  (e: 'load-new-data', time: number): void
}>()

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: IChartApi
let candleSeries: ISeriesApi<'Candlestick'>
let volumeSeries: ISeriesApi<'Histogram'>
let ma5MinSeries: ISeriesApi<'Line'>
let ma10MinSeries: ISeriesApi<'Line'>
let ma30MinSeries: ISeriesApi<'Line'>

const calculateMovingAverageSeriesData = (candleData: CandlestickData[], maLength: number) => {
  const maData = [] as LineData[]

  for (let i = 0; i < candleData.length; i++) {
    if (i < maLength) {
      // Provide whitespace data points until the MA can be calculated
      maData.push({ time: candleData[i].time } as LineData);
    } else {
      // Calculate the moving average, slow but simple way
      let sum = 0;
      for (let j = 0; j < maLength; j++) {
        sum += candleData[i - j].close;
      }
      const maValue = sum / maLength;
      maData.push({ time: candleData[i].time, value: maValue });
    }
  }

  return maData;
}

const initChart = () => {
  if (!chartContainer.value) return

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 600,
    layout: { background: { color: '#131722' }, textColor: '#d9d9d9' },
    grid: {
      vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
      horzLines: { color: 'rgba(42, 46, 57, 0.5)' }
    },
    crosshair: { mode: CrosshairMode.Normal },
    timeScale: { timeVisible: true, secondsVisible: false },
    handleScroll: { mouseWheel: true, pressedMouseMove: true },
    autoSize: true
  })

  candleSeries = chart.addSeries(CandlestickSeries, {
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001,
    },
    priceScaleId: 'price'
  })
  candleSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 },
  })

  volumeSeries = chart.addSeries(HistogramSeries, {
    priceFormat: {
      type: 'volume',
      precision: 4,
      minMove: 0.0001,
    },
    priceScaleId: 'volume'
  })
  volumeSeries.priceScale().applyOptions({
    scaleMargins: { top: 0.7, bottom: 0 },
  })

  ma5MinSeries = chart.addSeries(LineSeries,{
    color: '#FFA500',
    lineWidth: 2,
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001,
    }
  })
  ma5MinSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 },
  })

  ma10MinSeries = chart.addSeries(LineSeries,{
    color: '#00BFFF',
    lineWidth: 2,
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001,
    }
  })
  ma10MinSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 },
  })

  ma30MinSeries = chart.addSeries(LineSeries,{
    color: '#32CD32',
    lineWidth: 2,
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001,
    }
  })
  ma30MinSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 },
  })

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

  const ma5MinData: LineData[] = calculateMovingAverageSeriesData(candleData, 5)
  const ma10MinData: LineData[] = calculateMovingAverageSeriesData(candleData, 10)
  const ma30MinData: LineData[] = calculateMovingAverageSeriesData(candleData, 30)

  candleSeries.setData(candleData)
  volumeSeries.setData(volumeData)

  ma5MinSeries.setData(ma5MinData)
  ma10MinSeries.setData(ma10MinData)
  ma30MinSeries.setData(ma30MinData)
}

watch(() => props.data, updateChartData, { deep: true })
watch(() => props.pricePrecision, () => {
  candleSeries.applyOptions({ priceFormat: { precision: props.pricePrecision, type: 'price', minMove: 1 / Math.pow(10, props.pricePrecision) } })
})
watch(() => props.volumePrecision, () => {
  volumeSeries.applyOptions({ priceFormat: { type: 'volume', precision: props.volumePrecision } })
})

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
