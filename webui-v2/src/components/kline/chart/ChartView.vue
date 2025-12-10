<template>
  <div ref='chartContainer' class='kline-chart' :style='{ height: height, paddingTop: "8px" }' />
  <div :style='{ marginTop: "-" + height, zIndex: 10, position: "relative" }'>
    <div class='row text-neutral font-size-12' style='padding: 8px 0 0 8px'>
      {{ hoveringTime }}
      OPEN <span :style='{ color: digitsColor }' class='digits'>{{ hoveringCandleStick.open?.toFixed(10) || 0 }}</span>
      HIGH <span :style='{ color: digitsColor }' class='digits'>{{ hoveringCandleStick.high?.toFixed(10) || 0 }}</span>
      LOW <span :style='{ color: digitsColor }' class='digits'>{{ hoveringCandleStick.low?.toFixed(10) || 0 }}</span>
      CLOSE <span :style='{ color: digitsColor }' class='digits'>{{ hoveringCandleStick.close?.toFixed(10) || 0 }}</span>
      VOL <span :style='{ color: digitsColor }' class='digits'>{{ hoveringVolume.value?.toFixed(4) || 0 }}</span>
    </div>
    <div class='row text-grey-7 font-size-12' style='padding: 0 0 0 8px'>
      MA5 <span style='color: #FFA500' class='digits'>{{ hoveringMA5Min.value?.toFixed(10) || 0 }}</span>
      MA10 <span style='color: #00BFFF' class='digits'>{{ hoveringMA10Min.value?.toFixed(10) || 0 }}</span>
      MA30 <span style='color: #32CD32' class='digits'>{{ hoveringMA30Min.value?.toFixed(10) || 0 }}</span>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
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
  LineData,
  LineType,
  MouseEventParams
} from 'lightweight-charts'
import { KLineData } from './KlineData'

const props = defineProps({
  data: { type: Array as () => KLineData[], required: true, default: () => [] },
  pricePrecision: { type: Number, default: 10 },
  volumePrecision: { type: Number, default: 4 },
  height: { type: String, default: '550px' }
})

const hoveringTime = ref((() => {
  const now = new Date()
  return (now.toLocaleDateString() + ' ' + now.toLocaleTimeString()) as Time
})())
const hoveringCandleStick = ref({} as CandlestickData)
const hoveringVolume = ref({} as HistogramData)
const digitsColor = computed(() => hoveringCandleStick.value.open > hoveringCandleStick.value.close ? 'red' : hoveringCandleStick.value.open === hoveringCandleStick.value.close ? 'gray' : 'green')
const hoveringMA5Min = ref({} as LineData)
const hoveringMA10Min = ref({} as LineData)
const hoveringMA30Min = ref({} as LineData)

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
      maData.push({ time: candleData[i]?.time } as LineData)
    } else {
      let sum = 0
      for (let j = 0; j < maLength; j++) {
        sum += candleData[i - j]?.close || 0
      }
      const maValue = sum / maLength
      maData.push({ time: candleData[i]?.time as Time, value: maValue })
    }
  }

  return maData
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

  chart.applyOptions({
    timeScale: {
      timeVisible: true,
      secondsVisible: true,
      tickMarkFormatter: (time: Time) => {
        const date = new Date(time as number * 1000)
        return date.toLocaleTimeString()
      }
    },
    localization: {
      timeFormatter: (time: number) => {
        const date = new Date(time * 1000)
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
      }
    }
  })

  candleSeries = chart.addSeries(CandlestickSeries, {
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001
    },
    priceScaleId: 'price'
  })
  candleSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 }
  })

  volumeSeries = chart.addSeries(HistogramSeries, {
    priceFormat: {
      type: 'volume',
      precision: 4,
      minMove: 0.0001
    },
    priceScaleId: 'volume'
  })
  volumeSeries.priceScale().applyOptions({
    scaleMargins: { top: 0.7, bottom: 0 }
  })

  ma5MinSeries = chart.addSeries(LineSeries, {
    color: '#FFA500',
    lineWidth: 2,
    lineType: LineType.Curved,
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001
    }
  })
  ma5MinSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 }
  })

  ma10MinSeries = chart.addSeries(LineSeries, {
    color: '#00BFFF',
    lineWidth: 2,
    lineType: LineType.Curved,
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001
    }
  })
  ma10MinSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 }
  })

  ma30MinSeries = chart.addSeries(LineSeries, {
    color: '#32CD32',
    lineWidth: 2,
    lineType: LineType.Curved,
    priceFormat: {
      type: 'price',
      precision: 10,
      minMove: 0.0000000001
    }
  })
  ma30MinSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.2 }
  })

  chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRangeChange)

  chart.priceScale('price').applyOptions({
    visible: true,
    borderColor: '#555'
  })

  chart.priceScale('volume').applyOptions({
    visible: true,
    borderColor: '#555'
  })

  chart.subscribeCrosshairMove((param: MouseEventParams) => {
    if (!param.time) return

    const date = new Date(param.time as number * 1000)
    hoveringTime.value = (date.toLocaleDateString() + ' ' + date.toLocaleTimeString()) as Time

    const vol = param.seriesData.get(volumeSeries) as HistogramData
    if (vol !== undefined) {
      hoveringVolume.value = vol
    }

    const stick = param.seriesData.get(candleSeries) as CandlestickData
    if (stick !== undefined) {
      hoveringCandleStick.value = stick
    }

    const point1 = param.seriesData.get(ma5MinSeries) as LineData
    if (point1 !== undefined) {
      hoveringMA5Min.value = point1
    }

    const point2 = param.seriesData.get(ma10MinSeries) as LineData
    if (point2 !== undefined) {
      hoveringMA10Min.value = point2
    }

    const point3 = param.seriesData.get(ma30MinSeries) as LineData
    if (point3 !== undefined) {
      hoveringMA30Min.value = point3
    }
  })
}

const handleVisibleRangeChange = (logicalRange: { from: number; to: number } | null) => {
  if (!logicalRange) return
  if (!props.data.length) return

  const fromIndex = Math.max(Math.floor(logicalRange.from), 0)
  const toIndex = Math.min(Math.ceil(logicalRange.to), props.data.length - 1)

  const firstVisibleTime = props.data[fromIndex]?.time || 0
  const lastVisibleTime = props.data[toIndex]?.time || 0

  if (props.data[0] && firstVisibleTime && firstVisibleTime <= props.data[0].time) {
    emit('load-old-data', props.data[0]?.time)
  }
  const lastIndex = props.data.length - 1
  if (props.data[lastIndex] && lastVisibleTime && lastVisibleTime >= props.data[lastIndex].time) {
    emit('load-new-data', props.data[lastIndex]?.time)
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

<style scoped lang='sass'>
.kline-chart
  width: 100%
  background-color: #131722

.digits
  margin: 0 4px
</style>
