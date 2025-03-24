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
import { defineAsyncComponent, ref, onMounted, computed } from 'vue'
import { ApolloClient } from '@apollo/client/core'
import gql from 'graphql-tag'
import { graphqlResult } from 'src/utils'
import { getAppClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { useHostStore } from 'src/mystore/host'
import { Pool } from 'src/stores/pool'
import { useSwapStore } from 'src/mystore/swap'

import VolumeBulletin from 'src/components/bulletin/Volume.vue'
import HolderBulletin from 'src/components/bulletin/Holder.vue'
import RemoveLiquidity from 'src/components/liquidity/RemoveLiquidity.vue'

const KLine = defineAsyncComponent(() => import('src/components/kline/KLine.vue'))
const Swap = defineAsyncComponent(() => import('src/components/swap/Swap.vue'))
const Trades = defineAsyncComponent(() => import('src/components/trades/Trades.vue'))
const AddLiquidity = defineAsyncComponent(() => import('src/components/liquidity/AddLiquidity.vue'))

const tab = ref('swap')

const swapChainID = ref(useHostStore().swapCreationChainId)

const getPools = async (url: string): Promise<Array<Pool>> => {
  const appOptions = /* await */ getAppClientOptions(url)
  const appApolloClient = new ApolloClient(appOptions)
  const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(appApolloClient)(() => useQuery(gql`
    query {
      getPools {
        id
        token0
        token1
      }
    }
  `, {
    endpoint: 'swap',
    chainId: swapChainID.value
  }, {
    fetchPolicy: 'network-only'
  }))

  return new Promise((resolve, reject) => {
    onResult((res) => {
      if (res.loading) return
      const pools = graphqlResult.data(res, 'getPools') as Array<Pool>
      resolve(pools)
    })
    onError((error) => {
      reject(error)
    })
  })
}

const swapEndPoint = ref(useHostStore()._swapEndpoint())
const swapAppID = ref(useHostStore().swapApplicationId)
const swapService = ref(swapEndPoint.value + '/chains/' + swapChainID.value + '/applications/' + swapAppID.value)
const selectedToken = computed(() => useSwapStore().SelectedToken)

onMounted(async () => {
  const pools = await getPools(swapService.value)
  if (pools.findIndex((el) => el.token0 === selectedToken.value?.Address || el.token1 === selectedToken.value?.Address) < 0) {
    tab.value = 'addLiquidity'
  }
})

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
