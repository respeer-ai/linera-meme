<template>
  <div class='chart-wrapper' :style='{ height: height, position: "relative" }'>
    <div ref='chartContainer' class='kline-chart' />
    <!-- 右侧：交易信息 -->
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
  IPriceLine,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  CandlestickSeries,
  HistogramSeries,
  Time,
  LineSeries,
  LineData,
  LineType,
  LineStyle,
  MouseEventParams,
  AreaSeries
} from 'lightweight-charts'
import { useQuasar } from 'quasar'
import { KLineData } from './KlineData'
import { ChartType } from '../ChartType'
import { resolveVisibleRangeLoadDecision } from './visibleRangeLoad'
import {
  getChartDataRenderSignal,
  resolveSparseFirstRenderLogicalRange,
  resolveVisibleLogicalRangeAfterPrimaryRender,
  shouldAnchorLatestAfterBootstrapExpansion,
  shouldFitContentOnFirstRender,
  shouldScrollToLatestAfterIncrementalAppend,
  shouldScrollToLatestOnFirstRender,
  resolveVisibleLogicalRangeRestore,
  resolvePrimarySeriesRenderPlan,
  toCandlestickPoint,
  toLinePoint,
  toVolumePoint,
} from './chartDataUpdate'
import { createIndicatorRenderScheduler } from './indicatorRenderScheduler'

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
  showVolume: boolean
  showGrid: boolean
  showCrosshair: boolean
}

type BackgroundHistoryStatus = 'idle' | 'queued' | 'loading' | 'complete'

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
      volume: true,
      showVolume: true,
      showGrid: true,
      showCrosshair: true
    })
  },
  backgroundHistoryStatus: {
    type: String as () => BackgroundHistoryStatus,
    default: 'idle',
  },
})

const hoveringTime = ref((() => {
  const now = new Date()
  return (now.toLocaleDateString() + ' ' + now.toLocaleTimeString()) as Time
})())
const hoveringCandleStick = ref({} as CandlestickData)
const isHovering = ref(false)
const hoveringVolume = ref({} as HistogramData)
const hoveringMA5Min = ref({} as LineData)
const hoveringMA10Min = ref({} as LineData)
const hoveringMA30Min = ref({} as LineData)
const hoveringEMA7 = ref({} as LineData)
const hoveringEMA25 = ref({} as LineData)
const $q = useQuasar()

const PRICE_COLORS = {
  up: '#26a69a',
  down: '#ef5350',
  neutral: '#8A94A6'
} as const

const readThemeVar = (name: string, fallback: string) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.body).getPropertyValue(name).trim()
  return value || fallback
}

const hexToRgba = (hex: string, alpha: number) => {
  const normalized = hex.replace('#', '').trim()
  const full = normalized.length === 3
    ? normalized.split('').map((char) => char + char).join('')
    : normalized

  if (full.length !== 6) return `rgba(138, 148, 166, ${alpha})`

  const r = Number.parseInt(full.slice(0, 2), 16)
  const g = Number.parseInt(full.slice(2, 4), 16)
  const b = Number.parseInt(full.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

const getThemePalette = () => {
  const isDark = $q.dark.isActive
  const background = readThemeVar('--q-dark', isDark ? '#131722' : '#F6F8FB')
  const text = readThemeVar('--q-light', isDark ? '#d9d9d9' : '#0A0E17')
  const muted = readThemeVar('--q-neutral', '#8A94A6')
  const border = readThemeVar('--q-neutral-twenty-five', isDark ? '#2B2B43' : '#D7DCE5')

  return {
    background,
    text,
    muted,
    border,
    grid: isDark ? 'rgba(42, 46, 57, 0.5)' : hexToRgba(muted, 0.22),
    currentPriceLabelText: isDark ? '#ffffff' : '#F6F8FB',
    line: '#2962FF',
    areaTop: hexToRgba('#2962FF', isDark ? 0.4 : 0.24),
    areaBottom: hexToRgba('#2962FF', isDark ? 0 : 0.03)
  }
}

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

const chartDataRenderSignal = computed(() => getChartDataRenderSignal(props.data))
const hasDeferredIndicators = computed(() => (
  props.indicatorConfig.ma.enabled.ma5 ||
  props.indicatorConfig.ma.enabled.ma10 ||
  props.indicatorConfig.ma.enabled.ma30 ||
  props.indicatorConfig.ema.enabled.ema7 ||
  props.indicatorConfig.ema.enabled.ema25 ||
  props.indicatorConfig.boll
))
const indicatorRenderSignature = computed(() => JSON.stringify({
  data: chartDataRenderSignal.value,
  ma: props.indicatorConfig.ma.enabled,
  ema: props.indicatorConfig.ema.enabled,
  boll: props.indicatorConfig.boll,
}))

const trimTrailingZeros = (value: string) => value.replace(/\.?0+$/, '')

const formatCompactNumber = (value: number, fractionDigits = 2) => {
  const abs = Math.abs(value)
  if (abs >= 1e12) return trimTrailingZeros((value / 1e12).toFixed(fractionDigits)) + 'T'
  if (abs >= 1e9) return trimTrailingZeros((value / 1e9).toFixed(fractionDigits)) + 'B'
  if (abs >= 1e6) return trimTrailingZeros((value / 1e6).toFixed(fractionDigits)) + 'M'
  if (abs >= 1e3) return trimTrailingZeros((value / 1e3).toFixed(fractionDigits)) + 'K'
  return null
}

const getAxisPriceDecimals = (value: number) => {
  const abs = Math.abs(value)
  if (abs >= 100) return 2
  if (abs >= 1) return 4
  if (abs >= 0.01) return 4
  if (abs >= 0.0001) return 6
  if (abs >= 0.000001) return 8
  return Math.min(Math.max(props.pricePrecision, 8), 10)
}

const formatAxisPrice = (price: number) => {
  if (!Number.isFinite(price)) return '--'
  if (price === 0) return '0'

  const compact = formatCompactNumber(price, 2)
  if (compact) return compact

  return trimTrailingZeros(price.toFixed(getAxisPriceDecimals(price)))
}

const formatAxisVolume = (volume: number) => {
  if (!Number.isFinite(volume)) return '--'
  if (volume === 0) return '0'

  const compact = formatCompactNumber(volume, 2)
  if (compact) return compact

  const decimals = Math.min(props.volumePrecision, Math.abs(volume) >= 100 ? 0 : 2)
  return trimTrailingZeros(volume.toFixed(decimals))
}

const formatPrice = (price: number | undefined) => {
  if (price === undefined || !Number.isFinite(price)) return '--'
  return formatAxisPrice(price)
}

const formatVolume = (volume: number | undefined) => {
  if (volume === undefined || !Number.isFinite(volume)) return '--'
  return formatAxisVolume(volume)
}

const getPriceSeriesFormat = () => ({
  type: 'custom' as const,
  minMove: 1 / Math.pow(10, props.pricePrecision),
  formatter: formatAxisPrice
})

const getVolumeSeriesFormat = () => ({
  type: 'custom' as const,
  minMove: 1 / Math.pow(10, props.volumePrecision),
  formatter: formatAxisVolume
})

const getMainScaleMargins = () => (
  props.indicatorConfig.showVolume
    ? { top: 0.15, bottom: 0.3 }
    : { top: 0.12, bottom: 0.08 }
)

const applyPriceScaleLayout = () => {
  if (!chart) return
  const palette = getThemePalette()

  chart.priceScale('price').applyOptions({
    visible: true,
    borderColor: palette.border,
    scaleMargins: props.indicatorConfig.showVolume
      ? { top: 0.2, bottom: 0.28 }
      : { top: 0.16, bottom: 0.08 },
    entireTextOnly: true,
    minimumWidth: 86,
    alignLabels: true
  })

  chart.priceScale('volume').applyOptions({
    visible: props.indicatorConfig.showVolume,
    borderColor: palette.border,
    scaleMargins: { top: 0.76, bottom: 0.02 },
    entireTextOnly: true,
    minimumWidth: props.indicatorConfig.showVolume ? 72 : 0,
    alignLabels: true
  })
}

const getLatestPriceDirectionColor = () => {
  const latest = props.data[props.data.length - 1]
  if (!latest) return PRICE_COLORS.neutral

  if (props.chartType === ChartType.CANDLESTICK) {
    if (latest.close > latest.open) return PRICE_COLORS.up
    if (latest.close < latest.open) return PRICE_COLORS.down
    return PRICE_COLORS.neutral
  }

  const previous = props.data[props.data.length - 2]
  if (!previous) return PRICE_COLORS.neutral
  if (latest.close > previous.close) return PRICE_COLORS.up
  if (latest.close < previous.close) return PRICE_COLORS.down
  return PRICE_COLORS.neutral
}

const applyMainSeriesVisualState = () => {
  if (!mainSeries) return
  const latest = props.data[props.data.length - 1]
  const latestColor = getLatestPriceDirectionColor()
  const palette = getThemePalette()

  mainSeries.applyOptions({
    lastValueVisible: false,
    priceLineVisible: false
  })

  if (latestPriceLine) {
    mainSeries.removePriceLine(latestPriceLine)
    latestPriceLine = null
  }

  if (!latest) return

  latestPriceLine = mainSeries.createPriceLine({
    price: latest.close,
    color: latestColor,
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: '',
    lineVisible: true,
    axisLabelColor: latestColor,
    axisLabelTextColor: palette.currentPriceLabelText
  })
}

const applyThemeOptions = () => {
  if (!chart) return
  const palette = getThemePalette()

  chart.applyOptions({
    layout: {
      background: { color: palette.background },
      textColor: palette.text
    },
    grid: {
      vertLines: {
        color: palette.grid,
        visible: props.indicatorConfig.showGrid
      },
      horzLines: {
        color: palette.grid,
        visible: props.indicatorConfig.showGrid
      }
    },
    crosshair: {
      mode: props.indicatorConfig.showCrosshair ? CrosshairMode.Normal : CrosshairMode.Hidden
    },
    timeScale: {
      borderColor: palette.border
    }
  })

  applyPriceScaleLayout()
  applyMainSeriesVisualState()
}

const getChartHeight = () => {
  const parsedHeight = Number.parseInt(props.height, 10)
  return Number.isFinite(parsedHeight) ? parsedHeight : 550
}

const emit = defineEmits<{
  (e: 'load-old-data', time: number): void
  (e: 'load-new-data', time: number): void
  (e: 'indicators-ready'): void
}>()

const INITIAL_TIME_SCALE_RIGHT_OFFSET = 2
const MIN_DATA_POINTS_TO_ANCHOR_LATEST = INITIAL_TIME_SCALE_RIGHT_OFFSET + 2
const DEFAULT_TIME_SCALE_BAR_SPACING = 9

const chartContainer = ref<HTMLDivElement | null>(null)
let chart: IChartApi
let mainSeries: ISeriesApi<'Candlestick'> | ISeriesApi<'Line'> | ISeriesApi<'Area'>
let volumeSeries: ISeriesApi<'Histogram'> | null = null
let ma5MinSeries: ISeriesApi<'Line'> | null = null
let ma10MinSeries: ISeriesApi<'Line'> | null = null
let ma30MinSeries: ISeriesApi<'Line'> | null = null
let ema7Series: ISeriesApi<'Line'> | null = null
let ema25Series: ISeriesApi<'Line'> | null = null
let bollUpperSeries: ISeriesApi<'Line'> | null = null
let bollMiddleSeries: ISeriesApi<'Line'> | null = null
let bollLowerSeries: ISeriesApi<'Line'> | null = null
let latestPriceLine: IPriceLine | null = null
let resizeObserver: ResizeObserver | null = null
let pendingScrollToLatestFrame: number | null = null
let pendingFitContentFrame: number | null = null
let pendingSparseRangeFrame: number | null = null
let lastRenderedPrimarySeriesData: KLineData[] = []
const indicatorRenderScheduler = createIndicatorRenderScheduler({
  schedule: (run) => window.setTimeout(run, 0),
  cancel: (handle) => window.clearTimeout(handle),
  run: (signature) => {
    if (signature !== indicatorRenderSignature.value) return
    renderIndicatorsForCurrentData()
  },
})

const getVisibleLogicalRange = () => chart?.timeScale().getVisibleLogicalRange() || null

const logTimeScaleState = (event: string, extra: Record<string, unknown> = {}) => {
  const range = getVisibleLogicalRange()
  const timeScale = chart?.timeScale?.()
  console.info('[ChartView]', JSON.stringify({
    event,
    dataLength: props.data.length,
    visibleRange: range ? { from: range.from, to: range.to } : null,
    rightOffset: timeScale?.options?.()?.rightOffset ?? null,
    barSpacing: timeScale?.options?.()?.barSpacing ?? null,
    firstTime: props.data[0]?.time ?? null,
    lastTime: props.data[props.data.length - 1]?.time ?? null,
    ...extra,
  }))
}

const restoreVisibleLogicalRange = (range: { from: number; to: number } | null) => {
  if (!chart || !range) return
  logTimeScaleState('restore_visible_range_before', { targetRange: range })
  chart.timeScale().setVisibleLogicalRange(range)
  logTimeScaleState('restore_visible_range_after', { targetRange: range })
}

const scheduleScrollToLatest = () => {
  if (!chart) return

  if (pendingScrollToLatestFrame !== null) {
    window.cancelAnimationFrame(pendingScrollToLatestFrame)
  }
  if (pendingFitContentFrame !== null) {
    window.cancelAnimationFrame(pendingFitContentFrame)
    pendingFitContentFrame = null
  }

  pendingScrollToLatestFrame = window.requestAnimationFrame(() => {
    pendingScrollToLatestFrame = null
    chart?.timeScale().applyOptions({
      barSpacing: DEFAULT_TIME_SCALE_BAR_SPACING,
      rightOffset: INITIAL_TIME_SCALE_RIGHT_OFFSET,
    })
    logTimeScaleState('scroll_to_latest_before')
    chart?.timeScale().scrollToRealTime()
    logTimeScaleState('scroll_to_latest_after')
  })
}

const scheduleFitContent = () => {
  if (!chart) return

  if (pendingFitContentFrame !== null) {
    window.cancelAnimationFrame(pendingFitContentFrame)
  }

  pendingFitContentFrame = window.requestAnimationFrame(() => {
    pendingFitContentFrame = null
    logTimeScaleState('fit_content_before')
    chart?.timeScale().fitContent()
    logTimeScaleState('fit_content_after')
  })
}

const scheduleSparseFirstRenderRange = (range: { from: number; to: number }) => {
  if (!chart) return

  if (pendingSparseRangeFrame !== null) {
    window.cancelAnimationFrame(pendingSparseRangeFrame)
  }
  if (pendingScrollToLatestFrame !== null) {
    window.cancelAnimationFrame(pendingScrollToLatestFrame)
    pendingScrollToLatestFrame = null
  }
  if (pendingFitContentFrame !== null) {
    window.cancelAnimationFrame(pendingFitContentFrame)
    pendingFitContentFrame = null
  }

  pendingSparseRangeFrame = window.requestAnimationFrame(() => {
    pendingSparseRangeFrame = null
    chart?.timeScale().applyOptions({
      barSpacing: DEFAULT_TIME_SCALE_BAR_SPACING,
      rightOffset: INITIAL_TIME_SCALE_RIGHT_OFFSET,
    })
    logTimeScaleState('apply_sparse_first_render_range_before', { targetRange: range })
    chart?.timeScale().setVisibleLogicalRange(range)
    logTimeScaleState('apply_sparse_first_render_range_after', { targetRange: range })
  })
}

const rebuildSeriesPreservingVisibleRange = (rebuild: () => void) => {
  const previousVisibleLogicalRange = getVisibleLogicalRange()
  const previousData = lastRenderedPrimarySeriesData.map((point) => ({ ...point }))

  rebuild()
  updateChartData()

  restoreVisibleLogicalRange(resolveVisibleLogicalRangeRestore({
    previousData,
    nextData: props.data,
    previousRange: previousVisibleLogicalRange,
  }))
}

const clearIndicatorSeries = () => {
  ma5MinSeries?.setData([])
  ma10MinSeries?.setData([])
  ma30MinSeries?.setData([])
  ema7Series?.setData([])
  ema25Series?.setData([])
  bollUpperSeries?.setData([])
  bollMiddleSeries?.setData([])
  bollLowerSeries?.setData([])
}

const updateLatestIndicatorHoverState = ({
  ma5MinData,
  ma10MinData,
  ma30MinData,
  ema7Data,
  ema25Data,
}: {
  ma5MinData: LineData[] | undefined
  ma10MinData: LineData[] | undefined
  ma30MinData: LineData[] | undefined
  ema7Data: LineData[] | undefined
  ema25Data: LineData[] | undefined
}) => {
  if (isHovering.value) return

  const latestMA5 = ma5MinData?.[ma5MinData.length - 1]
  if (latestMA5?.value !== undefined) hoveringMA5Min.value = latestMA5

  const latestMA10 = ma10MinData?.[ma10MinData.length - 1]
  if (latestMA10?.value !== undefined) hoveringMA10Min.value = latestMA10

  const latestMA30 = ma30MinData?.[ma30MinData.length - 1]
  if (latestMA30?.value !== undefined) hoveringMA30Min.value = latestMA30

  const latestEMA7 = ema7Data?.[ema7Data.length - 1]
  if (latestEMA7?.value !== undefined) hoveringEMA7.value = latestEMA7

  const latestEMA25 = ema25Data?.[ema25Data.length - 1]
  if (latestEMA25?.value !== undefined) hoveringEMA25.value = latestEMA25
}

const renderIndicatorsForCurrentData = () => {
  if (!props.data.length || !hasDeferredIndicators.value) {
    clearIndicatorSeries()
    return
  }

  const candleData = props.data.map(toCandlestickPoint)

  let ma5MinData: LineData[] | undefined
  let ma10MinData: LineData[] | undefined
  let ma30MinData: LineData[] | undefined
  let ema7Data: LineData[] | undefined
  let ema25Data: LineData[] | undefined

  if (ma5MinSeries && props.indicatorConfig.ma.enabled.ma5) {
    ma5MinData = calculateMovingAverageSeriesData(candleData, 5)
    ma5MinSeries.setData(ma5MinData)
  } else {
    ma5MinSeries?.setData([])
  }

  if (ma10MinSeries && props.indicatorConfig.ma.enabled.ma10) {
    ma10MinData = calculateMovingAverageSeriesData(candleData, 10)
    ma10MinSeries.setData(ma10MinData)
  } else {
    ma10MinSeries?.setData([])
  }

  if (ma30MinSeries && props.indicatorConfig.ma.enabled.ma30) {
    ma30MinData = calculateMovingAverageSeriesData(candleData, 30)
    ma30MinSeries.setData(ma30MinData)
  } else {
    ma30MinSeries?.setData([])
  }

  if (ema7Series && props.indicatorConfig.ema.enabled.ema7) {
    ema7Data = calculateEMASeriesData(candleData, 7)
    ema7Series.setData(ema7Data)
  } else {
    ema7Series?.setData([])
  }

  if (ema25Series && props.indicatorConfig.ema.enabled.ema25) {
    ema25Data = calculateEMASeriesData(candleData, 25)
    ema25Series.setData(ema25Data)
  } else {
    ema25Series?.setData([])
  }

  if (bollUpperSeries && bollMiddleSeries && bollLowerSeries && props.indicatorConfig.boll) {
    const bollData = calculateBollingerBands(candleData, 20, 2)
    bollUpperSeries.setData(bollData.upper)
    bollMiddleSeries.setData(bollData.middle)
    bollLowerSeries.setData(bollData.lower)
  } else {
    bollUpperSeries?.setData([])
    bollMiddleSeries?.setData([])
    bollLowerSeries?.setData([])
  }

  updateLatestIndicatorHoverState({
    ma5MinData,
    ma10MinData,
    ma30MinData,
    ema7Data,
    ema25Data,
  })
  emit('indicators-ready')
}

const syncChartSize = () => {
  if (!chart || !chartContainer.value) return

  chart.applyOptions({
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight || getChartHeight()
  })
}

const resetHoverToLatest = () => {
  isHovering.value = false
  const latestData = props.data[props.data.length - 1]
  if (!latestData) return

  const date = new Date(latestData.time * 1000)
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  hoveringTime.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}` as Time
  hoveringCandleStick.value = {
    time: latestData.time as Time,
    open: latestData.open,
    high: latestData.high,
    low: latestData.low,
    close: latestData.close
  }
  hoveringVolume.value = {
    time: latestData.time as Time,
    value: latestData.volume,
    color: latestData.close >= latestData.open ? PRICE_COLORS.up : PRICE_COLORS.down
  }
}

const handleMouseLeave = () => {
  resetHoverToLatest()
}

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
  const palette = getThemePalette()

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: chartContainer.value.clientHeight || getChartHeight(),
    layout: { background: { color: palette.background }, textColor: palette.text },
    grid: {
      vertLines: { color: palette.grid, visible: props.indicatorConfig.showGrid },
      horzLines: { color: palette.grid, visible: props.indicatorConfig.showGrid }
    },
    crosshair: {
      mode: props.indicatorConfig.showCrosshair ? CrosshairMode.Normal : CrosshairMode.Hidden
    },
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      barSpacing: 9,
      minBarSpacing: 5,
      rightOffset: INITIAL_TIME_SCALE_RIGHT_OFFSET
    },
    handleScroll: { mouseWheel: true, pressedMouseMove: true },
    autoSize: false
  })

  chart.applyOptions({
    timeScale: {
      timeVisible: true,
      secondsVisible: false,
      borderColor: palette.border,
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

  applyPriceScaleLayout()

  chart.subscribeCrosshairMove(handleCrosshairMove)

  chartContainer.value.addEventListener('mouseleave', handleMouseLeave)

  resizeObserver = new ResizeObserver(() => {
    syncChartSize()
  })
  resizeObserver.observe(chartContainer.value)

  resetHoverToLatest()
}

const createMainSeries = () => {
  // 移除旧的主图系列
  if (mainSeries) {
    latestPriceLine = null
    chart.removeSeries(mainSeries)
  }

  // 根据图表类型创建新系列
  if (props.chartType === ChartType.CANDLESTICK) {
    mainSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceFormat: getPriceSeriesFormat(),
      priceScaleId: 'price'
    })
  } else if (props.chartType === ChartType.LINE) {
    mainSeries = chart.addSeries(LineSeries, {
      color: getThemePalette().line,
      lineWidth: 2,
      priceFormat: getPriceSeriesFormat(),
      priceScaleId: 'price'
    })
  } else if (props.chartType === ChartType.AREA) {
    const palette = getThemePalette()
    mainSeries = chart.addSeries(AreaSeries, {
      lineColor: palette.line,
      topColor: palette.areaTop,
      bottomColor: palette.areaBottom,
      lineWidth: 2,
      priceFormat: getPriceSeriesFormat(),
      priceScaleId: 'price'
    })
  }

  mainSeries.priceScale().applyOptions({
    scaleMargins: getMainScaleMargins()
  })

  applyMainSeriesVisualState()
  lastRenderedPrimarySeriesData = []
}

const createVolumeSeries = () => {
  if (!props.indicatorConfig.showVolume) {
    if (volumeSeries) {
      chart.removeSeries(volumeSeries)
      volumeSeries = null
    }
    applyPriceScaleLayout()
    return
  }

  if (volumeSeries) {
    chart.removeSeries(volumeSeries)
  }

  volumeSeries = chart.addSeries(HistogramSeries, {
    priceFormat: getVolumeSeriesFormat(),
    priceScaleId: 'volume'
  })
  volumeSeries.priceScale().applyOptions({
    scaleMargins: { top: 0.85, bottom: 0 }
  })
  applyPriceScaleLayout()
}

const createIndicatorSeries = () => {
  // 清除旧的指标系列
  if (ma5MinSeries) chart.removeSeries(ma5MinSeries)
  if (ma10MinSeries) chart.removeSeries(ma10MinSeries)
  if (ma30MinSeries) chart.removeSeries(ma30MinSeries)
  if (ema7Series) chart.removeSeries(ema7Series)
  if (ema25Series) chart.removeSeries(ema25Series)
  if (bollUpperSeries) chart.removeSeries(bollUpperSeries)
  if (bollMiddleSeries) chart.removeSeries(bollMiddleSeries)
  if (bollLowerSeries) chart.removeSeries(bollLowerSeries)
  ma5MinSeries = null
  ma10MinSeries = null
  ma30MinSeries = null
  ema7Series = null
  ema25Series = null
  bollUpperSeries = null
  bollMiddleSeries = null
  bollLowerSeries = null

  // 创建 MA 指标
  if (props.indicatorConfig.ma.enabled.ma5) {
    ma5MinSeries = chart.addSeries(LineSeries, {
      color: '#FFA500',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })
    ma5MinSeries.priceScale().applyOptions({
      scaleMargins: getMainScaleMargins()
    })
  }

  if (props.indicatorConfig.ma.enabled.ma10) {
    ma10MinSeries = chart.addSeries(LineSeries, {
      color: '#00BFFF',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })
    ma10MinSeries.priceScale().applyOptions({
      scaleMargins: getMainScaleMargins()
    })
  }

  if (props.indicatorConfig.ma.enabled.ma30) {
    ma30MinSeries = chart.addSeries(LineSeries, {
      color: '#32CD32',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })
    ma30MinSeries.priceScale().applyOptions({
      scaleMargins: getMainScaleMargins()
    })
  }

  // 创建 EMA 指标
  if (props.indicatorConfig.ema.enabled.ema7) {
    ema7Series = chart.addSeries(LineSeries, {
      color: '#FF69B4',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })
    ema7Series.priceScale().applyOptions({
      scaleMargins: getMainScaleMargins()
    })
  }

  if (props.indicatorConfig.ema.enabled.ema25) {
    ema25Series = chart.addSeries(LineSeries, {
      color: '#9370DB',
      lineWidth: 2,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })
    ema25Series.priceScale().applyOptions({
      scaleMargins: getMainScaleMargins()
    })
  }

  // 创建布林带指标
  if (props.indicatorConfig.boll) {
    bollUpperSeries = chart.addSeries(LineSeries, {
      color: 'rgba(180, 85, 255, 0.72)',
      lineWidth: 1,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })

    bollMiddleSeries = chart.addSeries(LineSeries, {
      color: 'rgba(244, 197, 66, 0.82)',
      lineWidth: 1,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })

    bollLowerSeries = chart.addSeries(LineSeries, {
      color: 'rgba(77, 212, 255, 0.72)',
      lineWidth: 1,
      lineType: LineType.Curved,
      priceFormat: getPriceSeriesFormat()
    })
  }
}

const handleCrosshairMove = (param: MouseEventParams) => {
  if (!param.time) {
    isHovering.value = false
    return
  }

  isHovering.value = true

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

  logTimeScaleState('visible_range_change', {
    logicalRange,
  })

  const fromIndex = Math.max(Math.floor(logicalRange.from), 0)
  const toIndex = Math.min(Math.ceil(logicalRange.to), props.data.length - 1)
  const loadDecision = resolveVisibleRangeLoadDecision({
    range: logicalRange,
    dataLength: props.data.length
  })

  const firstVisibleTime = props.data[fromIndex]?.time || 0
  const lastVisibleTime = props.data[toIndex]?.time || 0

  const lastIndex = props.data.length - 1
  for (const direction of loadDecision.loadOrder) {
    if (direction === 'new' && props.data[lastIndex] && lastVisibleTime && lastVisibleTime >= props.data[lastIndex].time) {
      emit('load-new-data', props.data[lastIndex]?.time)
    }
    if (direction === 'old' && props.data[0] && firstVisibleTime && firstVisibleTime <= props.data[0].time) {
      emit('load-old-data', props.data[0]?.time)
    }
  }
}

const updateChartData = () => {
  if (!mainSeries) return

  const previousVisibleLogicalRange = getVisibleLogicalRange()
  logTimeScaleState('update_chart_data_begin', {
    previousVisibleLogicalRange,
  })

  if (!props.data.length) {
    ;(mainSeries as ISeriesApi<'Candlestick'>).setData([])
    volumeSeries?.setData([])
    ma5MinSeries?.setData([])
    ma10MinSeries?.setData([])
    ma30MinSeries?.setData([])
    ema7Series?.setData([])
    ema25Series?.setData([])
    bollUpperSeries?.setData([])
    bollMiddleSeries?.setData([])
    bollLowerSeries?.setData([])
    lastRenderedPrimarySeriesData = []
    applyMainSeriesVisualState()
    return
  }

  const primaryRenderPlan = resolvePrimarySeriesRenderPlan({
    previous: lastRenderedPrimarySeriesData,
    next: props.data,
  })

  const hasIndicatorSeries = Boolean(
    ma5MinSeries ||
    ma10MinSeries ||
    ma30MinSeries ||
    ema7Series ||
    ema25Series ||
    bollUpperSeries ||
    bollMiddleSeries ||
    bollLowerSeries,
  )

  let candleData: CandlestickData[] | null = null

  if (props.chartType === ChartType.CANDLESTICK) {
    if (primaryRenderPlan.mode === 'full') {
      candleData = props.data.map(toCandlestickPoint)
      ;(mainSeries as ISeriesApi<'Candlestick'>).setData(candleData)
    } else if (primaryRenderPlan.mode === 'incremental') {
      for (const point of primaryRenderPlan.changedPoints) {
        ;(mainSeries as ISeriesApi<'Candlestick'>).update(toCandlestickPoint(point))
      }
    }
  } else if (props.chartType === ChartType.LINE || props.chartType === ChartType.AREA) {
    if (primaryRenderPlan.mode === 'full') {
      const lineData = props.data.map(toLinePoint)
      ;(mainSeries as ISeriesApi<'Line'>).setData(lineData)
    } else if (primaryRenderPlan.mode === 'incremental') {
      for (const point of primaryRenderPlan.changedPoints) {
        ;(mainSeries as ISeriesApi<'Line'>).update(toLinePoint(point))
      }
    }
  }

  applyMainSeriesVisualState()

  // 如果没有悬停，显示最新一根K线的数据
  if (!isHovering.value) {
    const latestData = props.data[props.data.length - 1]
    if (latestData) {
      const date = new Date(latestData.time * 1000)
      const year = date.getFullYear()
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const day = date.getDate().toString().padStart(2, '0')
      const hours = date.getHours().toString().padStart(2, '0')
      const minutes = date.getMinutes().toString().padStart(2, '0')
      const seconds = date.getSeconds().toString().padStart(2, '0')
      hoveringTime.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}` as Time
      hoveringCandleStick.value = {
        time: latestData.time as Time,
        open: latestData.open,
        high: latestData.high,
        low: latestData.low,
        close: latestData.close
      }
      hoveringVolume.value = {
        time: latestData.time as Time,
        value: latestData.volume,
        color: latestData.close >= latestData.open ? '#26a69a' : '#ef5350'
      }
    }
  }

  // 处理成交量
  if (props.indicatorConfig.showVolume) {
    if (primaryRenderPlan.mode === 'full') {
      const volumeData: HistogramData[] = props.data.map(toVolumePoint)
      volumeSeries?.setData(volumeData)
    } else if (primaryRenderPlan.mode === 'incremental') {
      for (const point of primaryRenderPlan.changedPoints) {
        volumeSeries?.update(toVolumePoint(point))
      }
    }
  }

  if (primaryRenderPlan.mode === 'full' && shouldScrollToLatestOnFirstRender({
    previousData: lastRenderedPrimarySeriesData,
    nextData: props.data,
    previousRange: previousVisibleLogicalRange,
    minimumDataPointsToAnchor: MIN_DATA_POINTS_TO_ANCHOR_LATEST,
  })) {
    logTimeScaleState('update_chart_data_decision', { action: 'scroll_to_latest_first_render', renderMode: primaryRenderPlan.mode })
    scheduleScrollToLatest()
  } else if (primaryRenderPlan.mode === 'full' && shouldAnchorLatestAfterBootstrapExpansion({
    previousData: lastRenderedPrimarySeriesData,
    nextData: props.data,
    minimumDataPointsToAnchor: MIN_DATA_POINTS_TO_ANCHOR_LATEST,
  })) {
    logTimeScaleState('update_chart_data_decision', { action: 'scroll_to_latest_bootstrap_expansion', renderMode: primaryRenderPlan.mode })
    scheduleScrollToLatest()
  } else if (primaryRenderPlan.mode === 'full' && shouldFitContentOnFirstRender({
    previousData: lastRenderedPrimarySeriesData,
    nextData: props.data,
    previousRange: previousVisibleLogicalRange,
    minimumDataPointsToAnchor: MIN_DATA_POINTS_TO_ANCHOR_LATEST,
  })) {
    const sparseRange = resolveSparseFirstRenderLogicalRange({
      previousData: lastRenderedPrimarySeriesData,
      nextData: props.data,
      previousRange: previousVisibleLogicalRange,
      minimumDataPointsToAnchor: MIN_DATA_POINTS_TO_ANCHOR_LATEST,
      rightOffset: INITIAL_TIME_SCALE_RIGHT_OFFSET,
    })

    if (sparseRange) {
      logTimeScaleState('update_chart_data_decision', { action: 'apply_sparse_first_render_range', renderMode: primaryRenderPlan.mode, targetRange: sparseRange })
      scheduleSparseFirstRenderRange(sparseRange)
    } else {
      logTimeScaleState('update_chart_data_decision', { action: 'fit_content_first_render', renderMode: primaryRenderPlan.mode })
      scheduleFitContent()
    }
  } else if (shouldScrollToLatestAfterIncrementalAppend({
    renderMode: primaryRenderPlan.mode,
    previousData: lastRenderedPrimarySeriesData,
    nextData: props.data,
    previousRange: previousVisibleLogicalRange,
  })) {
    logTimeScaleState('update_chart_data_decision', { action: 'scroll_to_latest_incremental_append', renderMode: primaryRenderPlan.mode })
    scheduleScrollToLatest()
  } else {
    logTimeScaleState('update_chart_data_decision', { action: 'restore_visible_range', renderMode: primaryRenderPlan.mode })
    restoreVisibleLogicalRange(resolveVisibleLogicalRangeAfterPrimaryRender({
      renderMode: primaryRenderPlan.mode,
      previousData: lastRenderedPrimarySeriesData,
      nextData: props.data,
      previousRange: previousVisibleLogicalRange,
    }))
  }

  if (!hasDeferredIndicators.value) {
    indicatorRenderScheduler.clear()
    clearIndicatorSeries()
    emit('indicators-ready')
  } else if (hasIndicatorSeries) {
    indicatorRenderScheduler.request(indicatorRenderSignature.value)
  }

  lastRenderedPrimarySeriesData = props.data.map((point) => ({ ...point }))
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

const calculateBollingerBands = (candleData: CandlestickData[], period: number = 20, stdDev: number = 2) => {
  const upper: LineData[] = []
  const middle: LineData[] = []
  const lower: LineData[] = []

  for (let i = 0; i < candleData.length; i++) {
    if (i < period - 1) {
      upper.push({ time: candleData[i]?.time } as LineData)
      middle.push({ time: candleData[i]?.time } as LineData)
      lower.push({ time: candleData[i]?.time } as LineData)
    } else {
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += candleData[i - j]?.close || 0
      }
      const sma = sum / period

      let variance = 0
      for (let j = 0; j < period; j++) {
        const diff = (candleData[i - j]?.close || 0) - sma
        variance += diff * diff
      }
      const std = Math.sqrt(variance / period)

      middle.push({ time: candleData[i]!.time as Time, value: sma })
      upper.push({ time: candleData[i]!.time as Time, value: sma + stdDev * std })
      lower.push({ time: candleData[i]!.time as Time, value: sma - stdDev * std })
    }
  }

  return { upper, middle, lower }
}

watch(chartDataRenderSignal, updateChartData)
watch(() => props.chartType, () => {
  rebuildSeriesPreservingVisibleRange(() => {
    createMainSeries()
  })
})
watch(() => props.indicatorConfig, () => {
  rebuildSeriesPreservingVisibleRange(() => {
    applyThemeOptions()
    createMainSeries()
    createIndicatorSeries()
    createVolumeSeries()
  })
}, { deep: true })
watch(() => props.pricePrecision, () => {
  if (mainSeries) {
    mainSeries.applyOptions({ priceFormat: getPriceSeriesFormat() })
  }
  if (ma5MinSeries) ma5MinSeries.applyOptions({ priceFormat: getPriceSeriesFormat() })
  if (ma10MinSeries) ma10MinSeries.applyOptions({ priceFormat: getPriceSeriesFormat() })
  if (ma30MinSeries) ma30MinSeries.applyOptions({ priceFormat: getPriceSeriesFormat() })
  if (ema7Series) ema7Series.applyOptions({ priceFormat: getPriceSeriesFormat() })
  if (ema25Series) ema25Series.applyOptions({ priceFormat: getPriceSeriesFormat() })
  if (bollUpperSeries) bollUpperSeries.applyOptions({ priceFormat: getPriceSeriesFormat() })
  if (bollMiddleSeries) bollMiddleSeries.applyOptions({ priceFormat: getPriceSeriesFormat() })
  if (bollLowerSeries) bollLowerSeries.applyOptions({ priceFormat: getPriceSeriesFormat() })
  applyPriceScaleLayout()
})
watch(() => props.volumePrecision, () => {
  if (volumeSeries) {
    volumeSeries.applyOptions({ priceFormat: getVolumeSeriesFormat() })
  }
})
watch(() => props.height, () => {
  syncChartSize()
})
watch(() => $q.dark.isActive, () => {
  if (!chart) return
  rebuildSeriesPreservingVisibleRange(() => {
    applyThemeOptions()
    createMainSeries()
    createIndicatorSeries()
    createVolumeSeries()
  })
})

onMounted(initChart)
onBeforeUnmount(() => {
  indicatorRenderScheduler.clear()
  if (pendingScrollToLatestFrame !== null) {
    window.cancelAnimationFrame(pendingScrollToLatestFrame)
    pendingScrollToLatestFrame = null
  }
  if (pendingFitContentFrame !== null) {
    window.cancelAnimationFrame(pendingFitContentFrame)
    pendingFitContentFrame = null
  }
  resizeObserver?.disconnect()
  if (chartContainer.value) {
    chartContainer.value.removeEventListener('mouseleave', handleMouseLeave)
  }
  if (mainSeries && latestPriceLine) {
    mainSeries.removePriceLine(latestPriceLine)
  }
  chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange)
  chart.remove()
})
</script>

<style scoped lang='sass'>
.chart-wrapper
  width: 100%
  position: relative
  background-color: var(--q-dark)
  color: var(--q-light)

.kline-chart
  width: 100%
  height: 100%

.price-info-overlay
  position: absolute
  top: 0
  left: 0
  pointer-events: none
  z-index: 10

.price-info-panel
  padding: 10px 12px
  pointer-events: none
  color: var(--q-light)

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
  color: var(--q-neutral)
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
  color: var(--q-neutral-light)
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
    color: var(--q-neutral-light)

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
    color: var(--q-neutral-light)
    background-color: var(--q-neutral-twenty-five)

.volume-item
  display: flex
  align-items: center
  gap: 4px
  margin-left: 4px

.volume-label
  color: var(--q-neutral-light)
  font-size: 11px
  font-weight: 500

.volume-value
  color: var(--q-light)
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
