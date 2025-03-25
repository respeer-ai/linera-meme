<template>
  <div class='row vertical-card-align bg-grey-2'>
    <div class='kline'>
      <div class='bg-white'>
        <KLine />
      </div>
      <div class='bg-white history'>
        <Trades />
      </div>
    </div>
    <q-space />
    <div class='swap vertical-card-padding'>
      <q-tabs v-model='tab' dense>
        <q-tab name='swap' label='Swap' />
        <q-tab name='addLiquidity' label='Add Liquidity' />
        <q-tab name='removeLiquidity' label='Remove Liquidity' />
      </q-tabs>
      <q-separator />
      <q-tab-panels v-model='tab' animated>
        <q-tab-panel name='swap'>
          <Swap />
        </q-tab-panel>
        <q-tab-panel name='addLiquidity'>
          <AddLiquidity />
        </q-tab-panel>
        <q-tab-panel name='removeLiquidity'>
          <RemoveLiquidity />
        </q-tab-panel>
      </q-tab-panels>
      <div class='bg-white vertical-card-align bulletin-padding'>
        <VolumeBulletin />
      </div>
      <div class='bg-white vertical-card-align bulletin-padding'>
        <HolderBulletin />
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue'

import VolumeBulletin from 'src/components/bulletin/Volume.vue'
import HolderBulletin from 'src/components/bulletin/Holder.vue'
import RemoveLiquidity from 'src/components/liquidity/RemoveLiquidity.vue'
import KLine from 'src/components/kline/KLine.vue'
import Swap from 'src/components/swap/Swap.vue'
import Trades from 'src/components/trades/Trades.vue'
import AddLiquidity from './AddLiquidity.vue'

const tab = ref('swap')

</script>

<style scoped lang='sass'>
.swap
  width: 360px
  margin-left: 4px

.swap-padding
  padding: 0 16px

.bulletin-padding
  padding: 16px

.kline
  width: calc(100% - 360px - 4px)

.history
  margin-top: 4px
</style>
