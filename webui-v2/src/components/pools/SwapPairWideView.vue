<template>
  <q-card flat class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md'>
    <pool-logo-view
      :token0-application='(token0Application as ams.Application)'
      :token1-application='(token1Application as ams.Application)'
    />
    <div class='row q-mt-lg'>
      <div class='bg-dark radius-8 q-px-md q-py-md' style='width: calc(50% - 8px);'>
        <div class='text-neutral font-size-16'>Total Liquidity</div>
        <div class='q-mt-sm font-size-20'>123,456 TLINERA</div>
      </div>
      <div class='bg-dark radius-8 q-px-md q-py-md q-ml-md' style='width: calc(50% - 8px);'>
        <div class='text-neutral font-size-16'>24H Volume</div>
        <div class='q-mt-sm font-size-20'>123,456 TLINERA</div>
      </div>
    </div>
    <div class='row q-mt-md'>
      <div class='bg-dark radius-8 q-px-md q-py-md' style='width: calc(50% - 8px);'>
        <div class='text-neutral font-size-16'>Mining APY</div>
        <div class='q-mt-sm font-size-20 text-mining'>12.34 %</div>
      </div>
      <div class='bg-dark radius-8 q-px-md q-py-md q-ml-md' style='width: calc(50% - 8px);'>
        <div class='text-neutral font-size-16'>Pool Rank</div>
        <div class='q-mt-sm font-size-20'>#1</div>
      </div>
    </div>
    <div class='row q-mt-md'>
      <q-btn no-caps rounded style='width: calc(50% - 8px);' class='bg-primary'>
        <div class='row flex justify-center items-center'>
          <q-icon name='add' color='white' size='16px' />
          <span class='q-ml-xs'>Add Liquidity</span>
        </div>
      </q-btn>
      <q-btn no-caps rounded style='width: calc(50% - 8px);' class='q-ml-md border-primary-50'>
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

interface Props {
  pool: Pool
}
const props = defineProps<Props>()
const pool = toRef(props, 'pool')

const token0Application = computed(() => ams.Ams.application(pool.value?.token0))
const token1Application = computed(() => ams.Ams.application(pool.value?.token1))

</script>