<template>
  <div class='chart-wrapper' :style='{ height: height, position: "relative" }'>
    <div ref='chartContainer' class='kline-chart' />
    <div class='price-info-overlay'>
      <div class='price-info-panel'>
        <!-- 时间和OHLC -->
        <div class='info-line primary'>
          <span class='time'>{{ hoveringTime }}</span>
          <span class='ohlc-group'>
            <span class='ohlc-item'>
              <span class='ohlc-label'>O</span>
              <span :class='["ohlc-value", priceChangeClass]'>{{ formatPrice(hoveringCandleStick.open) }}</span>
            </span>
            <span class='ohlc-item'>
              <span class='ohlc-label'>H</span>
              <span :class='["ohlc-value", priceChangeClass]'>{{ formatPrice(hoveringCandleStick.high) }}</span>
            </span>
            <span class='ohlc-item'>
              <span class='ohlc-label'>L</span>
              <span :class='["ohlc-value", priceChangeClass]'>{{ formatPrice(hoveringCandleStick.low) }}</span>
            </span>
            <span class='ohlc-item'>
              <span class='ohlc-label'>C</span>
              <span :class='["ohlc-value", priceChangeClass]'>{{ formatPrice(hoveringCandleStick.close) }}</span>
            </span>
          </span>
          <span class='change-badge' :class='priceChangeClass' v-if='priceChangePercent !== null'>
            {{ priceChangePercent >= 0 ? '+' : '' }}{{ priceChangePercent.toFixed(2) }}%
          </span>
          <span class='volume-item'>
            <span class='volume-label'>Vol</span>
            <span class='volume-value'>{{ formatVolume(hoveringVolume.value) }}</span>
          </span>
        </div>
        <!-- 指标信息 -->
        <div class='info-line indicators' v-if='hasVisibleIndicators'>
          <template v-if='props.indicatorConfig.ma.enabled.ma5'>
            <span class='indicator-item'>
              <span class='indicator-name' style='color: #FFA500'>MA5</span>
              <span class='indicator-val' style='color: #FFA500'>{{ formatPrice(hoveringMA5Min.value) }}</span>
            </span>
          </template>
          <template v-if='props.indicatorConfig.ma.enabled.ma10'>
            <span class='indicator-item'>
              <span class='indicator-name' style='color: #00BFFF'>MA10</span>
              <span class='indicator-val' style='color: #00BFFF'>{{ formatPrice(hoveringMA10Min.value) }}</span>
            </span>
          </template>
          <template v-if='props.indicatorConfig.ma.enabled.ma30'>
            <span class='indicator-item'>
              <span class='indicator-name' style='color: #32CD32'>MA30</span>
              <span class='indicator-val' style='color: #32CD32'>{{ formatPrice(hoveringMA30Min.value) }}</span>
            </span>
          </template>
          <template v-if='props.indicatorConfig.ema.enabled.ema7'>
            <span class='indicator-item'>
              <span class='indicator-name' style='color: #FF69B4'>EMA7</span>
              <span class='indicator-val' style='color: #FF69B4'>{{ formatPrice(hoveringEMA7.value) }}</span>
            </span>
          </template>
          <template v-if='props.indicatorConfig.ema.enabled.ema25'>
            <span class='indicator-item'>
              <span class='indicator-name' style='color: #9370DB'>EMA25</span>
              <span class='indicator-val' style='color: #9370DB'>{{ formatPrice(hoveringEMA25.value) }}</span>
            </span>
          </template>
        </div>
      </div>
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
const hoveringMA5Min = ref({} as LineData)
const hoveringMA10Min = ref({} as LineData)
const hoveringMA30Min = ref({} as LineData)
const hoveringEMA7 = ref({} as LineData)
const hoveringEMA25 = ref({} as LineData)

const priceChangeClass = computed(() => {
  if (!hoveringCandleStick.value.open || !hoveringCandleStick.value.close) return 'neutral'
  return hoveringCandleStick.value.close > hoveringCandleStick.value.open ? 'up' :
         hoveringCandleStick.value.close < hoveringCandleStick.value.open ? 'down' : 'neutral'
})

const priceChangePercent = computed(() => {
  if (!hoveringCandleStick.value.open || !hoveringCandleStick.value.close) return null
  const change = ((hoveringCandleStick.value.close - hoveringCandleStick.value.open) / hoveringCandleStick.value.open) * 100
  return change
})

const hasVisibleIndicators = computed(() => {
  return props.indicatorConfig.ma.enabled.ma5 ||
         props.indicatorConfig.ma.enabled.ma10 ||
         props.indicatorConfig.ma.enabled.ma30 ||
         props.indicatorConfig.ema.enabled.ema7 ||
         props.indicatorConfig.ema.enabled.ema25
})

const formatPrice = (price: number | undefined) => {
  if (!price) return '--'
  return price.toFixed(props.pricePrecision)
}

const formatVolume = (volume: number | undefined) => {
  if (!volume) return '--'
  if (volume >= 1e9) return (volume / 1e9).toFixed(2) + 'B'
  if (volume >= 1e6) return (volume / 1e6).toFixed(2) + 'M'
  if (volume >= 1e3) return (volume / 1e3).toFixed(2) + 'K'
  return volume.toFixed(props.volumePrecision)
}

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
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      barSpacing: 8,
      minBarSpacing: 4,
      rightOffset: 12
    },
    handleScroll: { mouseWheel: true, pressedMouseMove: true },
    autoSize: true
  })

  chart.applyOptions({
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      borderColor: '#2B2B43',
      tickMarkFormatter: (time: Time) => {
        const date = new Date(time as number * 1000)
        const hours = date.getHours().toString().padStart(2, '0')
        const minutes = date.getMinutes().toString().padStart(2, '0')
        return `${hours}:${minutes}`
      }
    },
    localization: {
      timeFormatter: (time: number) => {
        const date = new Date(time * 1000)
        const month = (date.getMonth() + 1).toString().padStart(2, '0')
        const day = date.getDate().toString().padStart(2, '0')
        const hours = date.getHours().toString().padStart(2, '0')
        const minutes = date.getMinutes().toString().padStart(2, '0')
        return `${month}-${day} ${hours}:${minutes}`
      }
    }
  })

  createMainSeries()
  createVolumeSeries()
  createIndicatorSeries()

  chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRangeChange)

  chart.priceScale('price').applyOptions({
    visible: true,
    borderColor: '#2B2B43',
    scaleMargins: { top: 0.1, bottom: 0.3 }
  })

  chart.priceScale('volume').applyOptions({
    visible: true,
    borderColor: '#2B2B43',
    scaleMargins: { top: 0.7, bottom: 0 }
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
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  hoveringTime.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}` as Time

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

  if (ema7Series) {
    const ema7Point = param.seriesData.get(ema7Series) as LineData
    if (ema7Point !== undefined) {
      hoveringEMA7.value = ema7Point
    }
  }

  if (ema25Series) {
    const ema25Point = param.seriesData.get(ema25Series) as LineData
    if (ema25Point !== undefined) {
      hoveringEMA25.value = ema25Point
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

  // 智能调整视图：限制可见数据点数量
  const dataLength = props.data.length
  if (dataLength > 0) {
    const maxVisibleBars = 120
    if (dataLength <= maxVisibleBars) {
      // 数据点少，自动适应
      chart.timeScale().fitContent()
    } else {
      // 数据点多，只显示最近的 maxVisibleBars 个
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, dataLength - maxVisibleBars),
        to: dataLength - 1
      })
    }
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
.chart-wrapper
  width: 100%
  position: relative
  background-color: #131722

.kline-chart
  width: 100%
  height: 100%

.price-info-overlay
  position: absolute
  top: 0
  left: 0
  right: 0
  pointer-events: none
  z-index: 10

.price-info-panel
  padding: 10px 12px
  pointer-events: none

.info-line
  display: flex
  align-items: center
  gap: 12px
  margin-bottom: 6px
  font-size: 12px
  line-height: 1.4

  &.primary
    margin-bottom: 4px

  &.indicators
    margin-bottom: 0

.time
  color: #b2b5be
  font-weight: 500
  font-size: 12px
  margin-right: 4px

.ohlc-group
  display: flex
  align-items: center
  gap: 10px

.ohlc-item
  display: flex
  align-items: center
  gap: 4px

.ohlc-label
  color: #787b86
  font-size: 11px
  font-weight: 500

.ohlc-value
  font-size: 12px
  font-weight: 600
  font-family: 'Roboto Mono', monospace

  &.up
    color: #26a69a

  &.down
    color: #ef5350

  &.neutral
    color: #b2b5be

.change-badge
  padding: 2px 8px
  border-radius: 4px
  font-size: 11px
  font-weight: 700
  font-family: 'Roboto Mono', monospace

  &.up
    color: #26a69a
    background-color: rgba(38, 166, 154, 0.15)

  &.down
    color: #ef5350
    background-color: rgba(239, 83, 80, 0.15)

  &.neutral
    color: #787b86
    background-color: rgba(120, 123, 134, 0.1)

.volume-item
  display: flex
  align-items: center
  gap: 4px
  margin-left: 4px

.volume-label
  color: #787b86
  font-size: 11px
  font-weight: 500

.volume-value
  color: #b2b5be
  font-size: 12px
  font-weight: 600
  font-family: 'Roboto Mono', monospace

.indicator-item
  display: flex
  align-items: center
  gap: 4px

.indicator-name
  font-size: 11px
  font-weight: 700

.indicator-val
  font-size: 11px
  font-weight: 600
  font-family: 'Roboto Mono', monospace

.digits
  margin: 0 4px
</style>
