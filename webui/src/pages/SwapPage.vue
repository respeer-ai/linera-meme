<template>
  <q-page class='flex justify-center' :style='{marginTop: "4px"}'>
    <div class='row vertical-card-align bg-grey-2' :style='{width: "1440px"}'>
      <div class='kline'>
        <div class='bg-white' style='height: 700px'>
          <KLineV2 />
        </div>
        <div class='bg-grey-1 history'>
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
        <div v-if='false' class='bg-white vertical-card-align bulletin-padding'>
          <VolumeBulletin />
        </div>
        <div v-if='false' class='bg-white vertical-card-align bulletin-padding'>
          <HolderBulletin />
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
import { onMounted, ref } from 'vue'
import { swap, notify, ams, proxy } from 'src/localstore'
import { Pool } from 'src/__generated__/graphql/swap/graphql'
import { useRoute } from 'vue-router'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'

import VolumeBulletin from 'src/components/bulletin/Volume.vue'
import HolderBulletin from 'src/components/bulletin/Holder.vue'
import RemoveLiquidity from 'src/components/liquidity/RemoveLiquidity.vue'
import KLineV2 from 'src/components/kline/KLineV2.vue'
import Swap from 'src/components/swap/Swap.vue'
import Trades from 'src/components/trades/Trades.vue'
import AddLiquidity from 'src/components/liquidity/AddLiquidity.vue'

interface Query {
  token0: string
  token1: string
}

const route = useRoute()
const token0 = ref((route.query as unknown as Query).token0)
const token1 = ref((route.query as unknown as Query).token1)

const tab = ref('swap')

const _swap = swap.useSwapStore()
const _ams = ams.useAmsStore()
const _proxy = proxy.useProxyStore()

const getPools = () => {
  _swap.getPools({
    Message: {
      Error: {
        Title: 'Get pools',
        Message: 'Failed get pools',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, (error: boolean, rows?: Pool[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

const getApplications = () => {
  _ams.getApplications({
    limit: 40,
    Message: {
      Error: {
        Title: 'Get applications',
        Message: 'Failed get applications',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, (error: boolean, rows?: ams.Application[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

const getMemeApplications = () => {
  _proxy.getApplications({
    Message: {
      Error: {
        Title: 'Get meme applications',
        Message: 'Failed get meme applications',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, (error: boolean, rows?: Chain[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

onMounted(() => {
  getPools()
  getApplications()
  getMemeApplications()
  _swap.selectedPool = _swap.getPool(token0.value, token1.value) as Pool
  _swap.selectedToken0 = token0.value
  _swap.selectedToken1 = token1.value
})

</script>

<style scoped lang='sass'>
.swap
  width: 380px
  margin-left: 4px
  margin-right: 4px
  .q-tabs
    height: 45px

.swap-padding
  padding: 0 16px

.bulletin-padding
  padding: 16px

.kline
  width: calc(100% - 380px - 8px)
  padding: 0 0 0 4px

.history
  margin-top: 4px
</style>
