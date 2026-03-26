<template>
  <q-btn-dropdown
    label='指标'
    icon='analytics'
    unelevated
    dense
    no-caps
    color='dark-secondary'
    text-color='neutral'
    dropdown-icon='expand_more'
    class='radius-8'
    style='min-width: 100px;'
  >
    <q-list dense class='bg-dark-secondary text-neutral' style='min-width: 200px;'>
      <!-- MA 指标 -->
      <q-item-label header class='text-grey-5 text-weight-bold q-px-sm'>
        移动平均线 (MA)
      </q-item-label>
      <q-item
        v-for='ma in maIndicators'
        :key='ma.key'
        clickable
        @click='toggleMA(ma.key)'
      >
        <q-item-section side>
          <q-toggle
            :model-value='isMAEnabled(ma.key)'
            color='primary'
            dense
            @update:model-value='toggleMA(ma.key)'
          />
        </q-item-section>
        <q-item-section>
          <q-item-label>
            MA({{ ma.period }})
            <span class='text-grey-6 q-ml-sm' :style='{ color: ma.color }'>━━</span>
          </q-item-label>
        </q-item-section>
      </q-item>

      <q-separator class='q-my-sm' />

      <!-- EMA 指标 -->
      <q-item-label header class='text-grey-5 text-weight-bold q-px-sm'>
        指数移动平均线 (EMA)
      </q-item-label>
      <q-item
        v-for='ema in emaIndicators'
        :key='ema.key'
        clickable
        @click='toggleEMA(ema.key)'
      >
        <q-item-section side>
          <q-toggle
            :model-value='isEMAEnabled(ema.key)'
            color='primary'
            dense
            @update:model-value='toggleEMA(ema.key)'
          />
        </q-item-section>
        <q-item-section>
          <q-item-label>
            EMA({{ ema.period }})
            <span class='text-grey-6 q-ml-sm' :style='{ color: ema.color }'>━━</span>
          </q-item-label>
        </q-item-section>
      </q-item>

      <q-separator class='q-my-sm' />

      <!-- BOLL 指标 -->
      <q-item clickable @click='toggleBOLL'>
        <q-item-section side>
          <q-toggle
            :model-value='bollEnabled'
            color='primary'
            dense
            @update:model-value='setBOLL'
          />
        </q-item-section>
        <q-item-section>
          <q-item-label>
            布林带 (BOLL)
            <span
              v-for='boll in bollIndicators'
              :key='boll.key'
              class='text-grey-6 q-ml-sm'
              :style='{ color: boll.color }'
            >
              {{ boll.label }}
            </span>
          </q-item-label>
        </q-item-section>
      </q-item>

      <q-separator class='q-my-sm' />

      <!-- 副图指标 -->
      <q-item-label header class='text-grey-5 text-weight-bold q-px-sm'>
        副图指标
      </q-item-label>
      <q-item clickable @click='toggleVolume'>
        <q-item-section side>
          <q-toggle
            :model-value='volumeEnabled'
            color='primary'
            dense
            @update:model-value='setVolume'
          />
        </q-item-section>
        <q-item-section>
          <q-item-label>成交量 (VOL)</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>
</template>

<script setup lang='ts'>
import { ref, watch } from 'vue'

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

const props = defineProps<{
  modelValue?: IndicatorConfig
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', config: IndicatorConfig): void
}>()

const maIndicators = [
  { key: 'ma5' as const, period: 5, color: '#FFA500' },
  { key: 'ma10' as const, period: 10, color: '#00BFFF' },
  { key: 'ma30' as const, period: 30, color: '#32CD32' }
]

const emaIndicators = [
  { key: 'ema7' as const, period: 7, color: '#FF69B4' },
  { key: 'ema25' as const, period: 25, color: '#9370DB' }
]

const bollIndicators = [
  { key: 'upper' as const, label: 'UP', color: '#B455FF' },
  { key: 'middle' as const, label: 'MID', color: '#F4C542' },
  { key: 'lower' as const, label: 'LOW', color: '#4DD4FF' }
]

const maEnabled = ref({
  ma5: props.modelValue?.ma.enabled.ma5 ?? true,
  ma10: props.modelValue?.ma.enabled.ma10 ?? true,
  ma30: props.modelValue?.ma.enabled.ma30 ?? true
})

const emaEnabled = ref({
  ema7: props.modelValue?.ema.enabled.ema7 ?? false,
  ema25: props.modelValue?.ema.enabled.ema25 ?? false
})

const bollEnabled = ref(props.modelValue?.boll ?? false)
const volumeEnabled = ref(props.modelValue?.volume ?? true)
const showVolume = ref(props.modelValue?.showVolume ?? true)
const showGrid = ref(props.modelValue?.showGrid ?? true)
const showCrosshair = ref(props.modelValue?.showCrosshair ?? true)

// 监听外部变化
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    maEnabled.value = { ...newVal.ma.enabled }
    emaEnabled.value = { ...newVal.ema.enabled }
    bollEnabled.value = newVal.boll
    volumeEnabled.value = newVal.volume
    showVolume.value = newVal.showVolume
    showGrid.value = newVal.showGrid
    showCrosshair.value = newVal.showCrosshair
  }
}, { deep: true })

const isMAEnabled = (key: keyof typeof maEnabled.value) => maEnabled.value[key]
const isEMAEnabled = (key: keyof typeof emaEnabled.value) => emaEnabled.value[key]

const toggleMA = (key: keyof typeof maEnabled.value) => {
  maEnabled.value[key] = !maEnabled.value[key]
  emitUpdate()
}

const toggleEMA = (key: keyof typeof emaEnabled.value) => {
  emaEnabled.value[key] = !emaEnabled.value[key]
  emitUpdate()
}

const toggleBOLL = () => {
  bollEnabled.value = !bollEnabled.value
  emitUpdate()
}

const setBOLL = (value: boolean) => {
  bollEnabled.value = value
  emitUpdate()
}

const toggleVolume = () => {
  volumeEnabled.value = !volumeEnabled.value
  showVolume.value = !showVolume.value
  emitUpdate()
}

const setVolume = (value: boolean) => {
  volumeEnabled.value = value
  showVolume.value = value
  emitUpdate()
}

const emitUpdate = () => {
  emit('update:modelValue', {
    ma: { enabled: { ...maEnabled.value } },
    ema: { enabled: { ...emaEnabled.value } },
    boll: bollEnabled.value,
    volume: volumeEnabled.value,
    showVolume: showVolume.value,
    showGrid: showGrid.value,
    showCrosshair: showCrosshair.value
  })
}
</script>
