<template>
  <q-dialog v-model='showDialog' position='right' full-height>
    <q-card class='bg-dark-secondary' style='width: 320px; max-width: 100vw; height: 100%;'>
      <q-card-section class='row items-center q-pb-none'>
        <div class='text-h6 text-neutral'>图表设置</div>
        <q-space />
        <q-btn icon='close' flat round dense v-close-popup />
      </q-card-section>

      <q-card-section class='q-pt-sm'>
        <!-- MA 设置 -->
        <div class='text-subtitle2 text-grey-5 q-mb-sm'>移动平均线 (MA)</div>
        <div class='row q-gutter-sm q-mb-md'>
          <div class='col-12'>
            <div class='row items-center q-gutter-sm'>
              <q-toggle v-model='config.ma.ma5' color='orange' dense />
              <span class='text-neutral'>MA(5)</span>
              <q-space />
              <q-input
                v-model.number='config.maPeriods.ma5'
                type='number'
                dense
                outlined
                dark
                style='width: 80px;'
                @update:model-value='emitUpdate'
              />
            </div>
          </div>
          <div class='col-12'>
            <div class='row items-center q-gutter-sm'>
              <q-toggle v-model='config.ma.ma10' color='cyan' dense />
              <span class='text-neutral'>MA(10)</span>
              <q-space />
              <q-input
                v-model.number='config.maPeriods.ma10'
                type='number'
                dense
                outlined
                dark
                style='width: 80px;'
                @update:model-value='emitUpdate'
              />
            </div>
          </div>
          <div class='col-12'>
            <div class='row items-center q-gutter-sm'>
              <q-toggle v-model='config.ma.ma30' color='green' dense />
              <span class='text-neutral'>MA(30)</span>
              <q-space />
              <q-input
                v-model.number='config.maPeriods.ma30'
                type='number'
                dense
                outlined
                dark
                style='width: 80px;'
                @update:model-value='emitUpdate'
              />
            </div>
          </div>
        </div>

        <!-- EMA 设置 -->
        <div class='text-subtitle2 text-grey-5 q-mb-sm'>指数移动平均线 (EMA)</div>
        <div class='row q-gutter-sm q-mb-md'>
          <div class='col-12'>
            <div class='row items-center q-gutter-sm'>
              <q-toggle v-model='config.ema.ema7' color='pink' dense />
              <span class='text-neutral'>EMA(7)</span>
              <q-space />
              <q-input
                v-model.number='config.emaPeriods.ema7'
                type='number'
                dense
                outlined
                dark
                style='width: 80px;'
                @update:model-value='emitUpdate'
              />
            </div>
          </div>
          <div class='col-12'>
            <div class='row items-center q-gutter-sm'>
              <q-toggle v-model='config.ema.ema25' color='purple' dense />
              <span class='text-neutral'>EMA(25)</span>
              <q-space />
              <q-input
                v-model.number='config.emaPeriods.ema25'
                type='number'
                dense
                outlined
                dark
                style='width: 80px;'
                @update:model-value='emitUpdate'
              />
            </div>
          </div>
        </div>

        <!-- BOLL 设置 -->
        <div class='text-subtitle2 text-grey-5 q-mb-sm'>布林带 (BOLL)</div>
        <div class='row q-gutter-sm q-mb-md items-center'>
          <q-toggle v-model='config.boll' color='purple' dense />
          <span class='text-neutral'>显示布林带</span>
          <q-space />
          <div class='row items-center q-gutter-xs'>
            <span class='text-grey-6'>周期</span>
            <q-input
              v-model.number='config.bollPeriod'
              type='number'
              dense
              outlined
              dark
              style='width: 60px;'
              @update:model-value='emitUpdate'
            />
          </div>
        </div>

        <!-- 显示设置 -->
        <q-separator class='q-my-md' />
        <div class='text-subtitle2 text-grey-5 q-mb-sm'>显示设置</div>
        <div class='column q-gutter-sm'>
          <div class='row items-center q-gutter-sm'>
            <q-toggle v-model='config.showVolume' color='primary' dense />
            <span class='text-neutral'>显示成交量</span>
          </div>
          <div class='row items-center q-gutter-sm'>
            <q-toggle v-model='config.showGrid' color='primary' dense />
            <span class='text-neutral'>显示网格</span>
          </div>
          <div class='row items-center q-gutter-sm'>
            <q-toggle v-model='config.showCrosshair' color='primary' dense />
            <span class='text-neutral'>显示十字线</span>
          </div>
        </div>

        <!-- 重置按钮 -->
        <q-separator class='q-my-md' />
        <q-btn
          outline
          color='primary'
          label='恢复默认设置'
          no-caps
          class='full-width'
          @click='resetConfig'
        />
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang='ts'>
import { ref } from 'vue'

export interface ChartSettingsConfig {
  ma: {
    ma5: boolean
    ma10: boolean
    ma30: boolean
  }
  maPeriods: {
    ma5: number
    ma10: number
    ma30: number
  }
  ema: {
    ema7: boolean
    ema25: boolean
  }
  emaPeriods: {
    ema7: number
    ema25: number
  }
  boll: boolean
  bollPeriod: number
  showVolume: boolean
  showGrid: boolean
  showCrosshair: boolean
}

const defaultConfig: ChartSettingsConfig = {
  ma: {
    ma5: true,
    ma10: true,
    ma30: true
  },
  maPeriods: {
    ma5: 5,
    ma10: 10,
    ma30: 30
  },
  ema: {
    ema7: false,
    ema25: false
  },
  emaPeriods: {
    ema7: 7,
    ema25: 25
  },
  boll: false,
  bollPeriod: 20,
  showVolume: true,
  showGrid: true,
  showCrosshair: true
}

const showDialog = ref(false)
const config = ref<ChartSettingsConfig>({ ...defaultConfig })

const emit = defineEmits<{
  (e: 'update:config', config: ChartSettingsConfig): void
}>()

const emitUpdate = () => {
  emit('update:config', { ...config.value })
}

const resetConfig = () => {
  config.value = { ...defaultConfig, maPeriods: { ...defaultConfig.maPeriods }, emaPeriods: { ...defaultConfig.emaPeriods } }
  emitUpdate()
}

const open = () => {
  showDialog.value = true
}

defineExpose({ open })
</script>
