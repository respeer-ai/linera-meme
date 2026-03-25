<template>
  <div class='chart-toolbar row items-center justify-between q-px-md q-py-xs bg-dark-secondary' style='border-bottom: 1px solid rgba(255,255,255,0.1);'>
    <!-- 左侧：图表类型 + 指标 + 时间周期 -->
    <div class='row items-center q-gutter-sm'>
      <chart-type-selector v-model='chartType' />
      <indicator-selector v-model='indicatorConfig' />
      <interval-selector-dropdown v-model='selectedInterval' />
    </div>

    <!-- 右侧：工具按钮 -->
    <div class='row items-center q-gutter-sm'>
      <q-btn
        :icon='isFullscreen ? "fullscreen_exit" : "fullscreen"'
        flat
        dense
        round
        color='neutral'
        size='sm'
        @click='toggleFullscreen'
      >
        <q-tooltip>全屏</q-tooltip>
      </q-btn>

      <q-btn
        icon='settings'
        flat
        dense
        round
        color='neutral'
        size='sm'
        @click='openSettings'
      >
        <q-tooltip>设置</q-tooltip>
      </q-btn>

      <q-btn
        icon='camera_alt'
        flat
        dense
        round
        color='neutral'
        size='sm'
        @click='takeScreenshot'
      >
        <q-tooltip>截图</q-tooltip>
      </q-btn>
    </div>
  </div>

  <!-- 设置面板 -->
  <chart-settings ref='chartSettingsRef' @update:config='onConfigUpdate' />
</template>

<script setup lang='ts'>
import { ref, watch } from 'vue'
import { Interval } from 'src/stores/kline/const'
import { ChartType } from './ChartType'
import type { IndicatorConfig } from './IndicatorSelector.vue'
import type { ChartSettingsConfig } from './ChartSettings.vue'
import ChartTypeSelector from './ChartTypeSelector.vue'
import IndicatorSelector from './IndicatorSelector.vue'
import IntervalSelectorDropdown from './IntervalSelectorDropdown.vue'
import ChartSettings from './ChartSettings.vue'

const props = defineProps({
  modelValue: {
    type: Object as () => {
      interval: Interval
      chartType: ChartType
      indicatorConfig: IndicatorConfig
    },
    required: true
  }
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: typeof props.modelValue): void
}>()

const selectedInterval = ref<Interval>(props.modelValue?.interval || Interval.FIVE_MINUTE)
const chartType = ref<ChartType>(props.modelValue?.chartType || ChartType.CANDLESTICK)
const indicatorConfig = ref<IndicatorConfig>(props.modelValue?.indicatorConfig || {
  ma: { enabled: { ma5: true, ma10: true, ma30: true } },
  ema: { enabled: { ema7: false, ema25: false } },
  boll: false,
  volume: true
})

const isFullscreen = ref(false)
const chartSettingsRef = ref<InstanceType<typeof ChartSettings> | null>(null)

// 监听内部状态变化，同步到外部
watch([selectedInterval, chartType, indicatorConfig], () => {
  console.log('[ChartToolbar] State changed, interval:', selectedInterval.value)
  emit('update:modelValue', {
    interval: selectedInterval.value,
    chartType: chartType.value,
    indicatorConfig: indicatorConfig.value
  })
}, { deep: true })

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    selectedInterval.value = newVal.interval
    chartType.value = newVal.chartType
    indicatorConfig.value = newVal.indicatorConfig
  }
}, { deep: true })

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

const openSettings = () => {
  chartSettingsRef.value?.open()
}

const onConfigUpdate = (config: ChartSettingsConfig) => {
  // 将设置转换为指标配置
  indicatorConfig.value = {
    ma: {
      enabled: {
        ma5: config.ma.ma5,
        ma10: config.ma.ma10,
        ma30: config.ma.ma30
      }
    },
    ema: {
      enabled: {
        ema7: config.ema.ema7,
        ema25: config.ema.ema25
      }
    },
    boll: config.boll,
    volume: config.showVolume
  }
  emit('update:modelValue', {
    interval: selectedInterval.value,
    chartType: chartType.value,
    indicatorConfig: indicatorConfig.value
  })
}

const takeScreenshot = () => {
  const chartElement = document.querySelector('.kline-chart')
  if (!chartElement) return

  // 使用 html2canvas 或直接使用 canvas 的 toDataURL
  const canvas = (chartElement as HTMLElement).querySelector('canvas')
  if (canvas) {
    const link = document.createElement('a')
    link.download = `kline-${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }
}
</script>

<style scoped lang='sass'>
.chart-toolbar
  min-height: 44px

:deep(.q-btn)
  &.outline
    border: 1px solid rgba(255, 255, 255, 0.12)
</style>
