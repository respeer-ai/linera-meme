<template>
  <q-card
    flat
    class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md'
    style='display: flex; flex-direction: column;'
  >
    <pool-logo-view
      :token0-application='(token0Application as ams.Application)'
      :token1-application='(token1Application as ams.Application)'
      :show-rank='false'
    />

    <div class='q-mt-lg'>
      <token-info-line-view
        label='Total Liquidity'
        value='123,456 TLINERA'
        value-color='light'
        :value-bold='true'
        :underline='false'
      />
      <div class='q-mt-sm'>
        <token-info-line-view
          label='24H Volume'
          value='123.456 TLINERA'
          value-color='light'
          :value-bold='true'
          :underline='false'
        />
      </div>
      <div class='q-mt-sm'>
        <token-info-line-view
          label='Mining APY'
          value='18.78%'
          value-color='mining'
          :value-bold='false'
          :underline='true'
        />
      </div>
    </div>

    <div class='q-mt-xl narrow-btn' style='margin-top: auto;'>
      <q-btn no-caps rounded class='bg-primary full-width'>
        <div class='row flex justify-center items-center'>
          <q-icon name='add' color='white' size='16px' />
          <span class='q-ml-xs'>Add Liquidity</span>
        </div>
      </q-btn>
      <q-btn no-caps rounded class='q-ml-md q-mt-sm border-primary-50 full-width'>
        <div class='row flex justify-center items-center'>
          <q-icon name='remove' color='white' size='16px' />
          <span class='q-ml-xs'>Remove</span>
        </div>
      </q-btn>
    </div>
  </q-card>
</template>

<script setup lang='ts'>
import { type Pool} from 'src/__generated__/graphql/swap/graphql'
import { computed, toRef } from 'vue'
import { ams } from 'src/stores/export'

import PoolLogoView from './PoolLogoView.vue'
import TokenInfoLineView from '../trade/TokenInfoLineView.vue'

interface Props {
  pool: Pool
}
const props = defineProps<Props>()
const pool = toRef(props, 'pool')

const token0Application = computed(() => ams.Ams.application(pool.value?.token0))
const token1Application = computed(() => ams.Ams.application(pool.value?.token1))

</script>