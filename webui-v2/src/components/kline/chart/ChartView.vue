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
  MouseEventParams,
  AreaSeries
} from 'lightweight-charts'
import { KLineData } from './KlineData'
import { ChartType } from '../ChartType'

export interface IndicatorConfig {
  ma: {
    enabled: {
      ma5: boolean
      ma10: boolean
      ma30: boolean
    }
  }
  ema: {
    enabled: {
      ema7: boolean
      ema25: boolean
    }
  }
  boll: boolean
  volume: boolean
}

const props = defineProps({
  data: { type: Array as () => KLineData[], required: true, default: () => [] },
  pricePrecision: { type: Number, default: 10 },
  volumePrecision: { type: Number, default: 4 },
  height: { type: String, default: '550px' },
  chartType: { type: String as () => ChartType, default: ChartType.CANDLESTICK },
  indicatorConfig: {
    type: Object as () => IndicatorConfig,
    default: () => ({
      ma: { enabled: { ma5: true, ma10: true, ma30: true } },
      ema: { enabled: { ema7: false, ema25: false } },
      boll: false,
      volume: true
    })
  }
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

const emit = defineEmits<{
  (e: 'load-old-data', time: number): void
  (e: 'load-new-data', time: number): void
}>()

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: IChartApi
let mainSeries: ISeriesApi<'Candlestick'> | ISeriesApi<'Line'> | ISeriesApi<'Area'>
let volumeSeries: ISeriesApi<'Histogram'>
let ma5MinSeries: ISeriesApi<'Line'> | null = null
let ma10MinSeries: ISeriesApi<'Line'> | null = null
let ma30MinSeries: ISeriesApi<'Line'> | null = null
let ema7Series: ISeriesApi<'Line'> | null = null
let ema25Series: ISeriesApi<'Line'> | null = null

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

  createMainSeries()
  createVolumeSeries()
  createIndicatorSeries()

  chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRangeChange)

  chart.priceScale('price').applyOptions({
    visible: true,
    borderColor: '#555'
  })

  chart.priceScale('volume').applyOptions({
    visible: true,
    borderColor: '#555'
  })

  chart.subscribeCrosshairMove(handleCrosshairMove)
}

const createMainSeries = () => {
  // 移除旧的主图系列
  if (mainSeries) {
    chart.removeSeries(mainSeries)
  }

  // 根据图表类型创建新系列
  if (props.chartType === ChartType.CANDLESTICK) {
    mainSeries = chart.addSeries(CandlestickSeries, {
      priceFormat: {
        type: 'price',
        precision: 10,
        minMove: 0.0000000001
      },
      priceScaleId: 'price'
    })
  } else if (props.chartType === ChartType.LINE) {
    mainSeries = chart.addSeries(LineSeries, {
      color: '#2962FF',
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 10,
        minMove: 0.0000000001
      },
      priceScaleId: 'price'
    })
  } else if (props.chartType === ChartType.AREA) {
    mainSeries = chart.addSeries(AreaSeries, {
      lineColor: '#2962FF',
      topColor: 'rgba(41, 98, 255, 0.4)',
      bottomColor: 'rgba(41, 98, 255, 0.0)',
      lineWidth: 2,
      priceFormat: {
        type: 'price',
        precision: 10,
        minMove: 0.0000000001
      },
      priceScaleId: 'price'
    })
  }

  mainSeries.priceScale().applyOptions({
    scaleMargins: { top: 0, bottom: 0.3 }
  })
}

const createVolumeSeries = () => {
  if (!props.indicatorConfig.volume) return

  if (volumeSeries) {
    chart.removeSeries(volumeSeries)
  }

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
}

const createIndicatorSeries = () => {
  // 清除旧的指标系列
  if (ma5MinSeries) chart.removeSeries(ma5MinSeries)
  if (ma10MinSeries) chart.removeSeries(ma10MinSeries)
  if (ma30MinSeries) chart.removeSeries(ma30MinSeries)
  if (ema7Series) chart.removeSeries(ema7Series)
  if (ema25Series) chart.removeSeries(ema25Series)

  ma5MinSeries = null
  ma10MinSeries = null
  ma30MinSeries = null
  ema7Series = null
  ema25Series = null

  // 创建 MA 指标
  if (props.indicatorConfig.ma.enabled.ma5) {
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
      scaleMargins: { top: 0, bottom: 0.3 }
    })
  }

  if (props.indicatorConfig.ma.enabled.ma10) {
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
      scaleMargins: { top: 0, bottom: 0.3 }
    })
  }

  if (props.indicatorConfig.ma.enabled.ma30) {
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
      scaleMargins: { top: 0, bottom: 0.3 }
    })
  }

  // 创建 EMA 指标
  if (props.indicatorConfig.ema.enabled.ema7) {
    ema7Series = chart.addSeries(LineSeries, {
      color: '#FF69B4',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceFormat: {
        type: 'price',
        precision: 10,
        minMove: 0.0000000001
      }
    })
    ema7Series.priceScale().applyOptions({
      scaleMargins: { top: 0, bottom: 0.3 }
    })
  }

  if (props.indicatorConfig.ema.enabled.ema25) {
    ema25Series = chart.addSeries(LineSeries, {
      color: '#9370DB',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceFormat: {
        type: 'price',
        precision: 10,
        minMove: 0.0000000001
      }
    })
    ema25Series.priceScale().applyOptions({
      scaleMargins: { top: 0, bottom: 0.3 }
    })
  }
}

const handleCrosshairMove = (param: MouseEventParams) => {
  if (!param.time) return

  const date = new Date(param.time as number * 1000)
  hoveringTime.value = (date.toLocaleDateString() + ' ' + date.toLocaleTimeString()) as Time

  if (volumeSeries) {
    const vol = param.seriesData.get(volumeSeries) as HistogramData
    if (vol !== undefined) {
      hoveringVolume.value = vol
    }
  }

  const mainData = param.seriesData.get(mainSeries)
  if (mainData !== undefined) {
    if (props.chartType === ChartType.CANDLESTICK) {
      hoveringCandleStick.value = mainData as CandlestickData
    } else {
      // 折线图和面积图只有收盘价
      const lineData = mainData as LineData
      hoveringCandleStick.value = {
        time: lineData.time,
        open: lineData.value || 0,
        high: lineData.value || 0,
        low: lineData.value || 0,
        close: lineData.value || 0
      } as CandlestickData
    }
  }

  if (ma5MinSeries) {
    const point1 = param.seriesData.get(ma5MinSeries) as LineData
    if (point1 !== undefined) {
      hoveringMA5Min.value = point1
    }
  }

  if (ma10MinSeries) {
    const point2 = param.seriesData.get(ma10MinSeries) as LineData
    if (point2 !== undefined) {
      hoveringMA10Min.value = point2
    }
  }

  if (ma30MinSeries) {
    const point3 = param.seriesData.get(ma30MinSeries) as LineData
    if (point3 !== undefined) {
      hoveringMA30Min.value = point3
    }
  }
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
  if (!mainSeries || !volumeSeries) return

  // 处理主图数据
  const candleData: CandlestickData[] = props.data.map(d => ({
    time: d.time as Time,
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close
  }))

  const lineData: LineData[] = props.data.map(d => ({
    time: d.time as Time,
    value: d.close
  }))

  if (props.chartType === ChartType.CANDLESTICK) {
    (mainSeries as ISeriesApi<'Candlestick'>).setData(candleData)
  } else if (props.chartType === ChartType.LINE || props.chartType === ChartType.AREA) {
    (mainSeries as ISeriesApi<'Line'>).setData(lineData)
  }

  // 处理成交量
  if (props.indicatorConfig.volume) {
    const volumeData: HistogramData[] = props.data.map(d => ({
      time: d.time as Time,
      value: d.volume,
      color: d.close >= d.open ? '#26a69a' : '#ef5350'
    }))
    volumeSeries.setData(volumeData)
  }

  // 处理 MA 指标
  if (ma5MinSeries && props.indicatorConfig.ma.enabled.ma5) {
    const ma5MinData: LineData[] = calculateMovingAverageSeriesData(candleData, 5)
    ma5MinSeries.setData(ma5MinData)
  }

  if (ma10MinSeries && props.indicatorConfig.ma.enabled.ma10) {
    const ma10MinData: LineData[] = calculateMovingAverageSeriesData(candleData, 10)
    ma10MinSeries.setData(ma10MinData)
  }

  if (ma30MinSeries && props.indicatorConfig.ma.enabled.ma30) {
    const ma30MinData: LineData[] = calculateMovingAverageSeriesData(candleData, 30)
    ma30MinSeries.setData(ma30MinData)
  }

  if (ema7Series && props.indicatorConfig.ema.enabled.ema7) {
    const ema7Data: LineData[] = calculateEMASeriesData(candleData, 7)
    ema7Series.setData(ema7Data)
  }

  if (ema25Series && props.indicatorConfig.ema.enabled.ema25) {
    const ema25Data: LineData[] = calculateEMASeriesData(candleData, 25)
    ema25Series.setData(ema25Data)
  }
}

const calculateEMASeriesData = (candleData: CandlestickData[], period: number) => {
  const emaData: LineData[] = []
  const multiplier = 2 / (period + 1)

  for (let i = 0; i < candleData.length; i++) {
    if (i < period - 1) {
      emaData.push({ time: candleData[i]?.time } as LineData)
    } else if (i === period - 1) {
      // SMA 作为初始 EMA
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += candleData[i - j]?.close || 0
      }
      emaData.push({ time: candleData[i]!.time as Time, value: sum / period })
    } else {
      // EMA = (Close - EMA(prev)) * multiplier + EMA(prev)
      const prevEMA = emaData[i - 1]!.value || 0
      const close = candleData[i]?.close || 0
      const emaValue = (close - prevEMA) * multiplier + prevEMA
      emaData.push({ time: candleData[i]!.time as Time, value: emaValue })
    }
  }

  return emaData
}

watch(() => props.data, updateChartData, { deep: true })
watch(() => props.chartType, () => {
  createMainSeries()
  updateChartData()
})
watch(() => props.indicatorConfig, () => {
  createIndicatorSeries()
  createVolumeSeries()
  updateChartData()
}, { deep: true })
watch(() => props.pricePrecision, () => {
  if (mainSeries) {
    mainSeries.applyOptions({ priceFormat: { precision: props.pricePrecision, type: 'price', minMove: 1 / Math.pow(10, props.pricePrecision) } })
  }
})
watch(() => props.volumePrecision, () => {
  if (volumeSeries) {
    volumeSeries.applyOptions({ priceFormat: { type: 'volume', precision: props.volumePrecision } })
  }
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
