<template>
  <q-page>
    <q-infinite-scroll @load='onLoad' :offset='300' :style='{padding: "0 8px"}'>
      <div class='row'>
        <div v-for='item in memeAppInfos' :key='item.appID' class='col-xs-12 col-sm-6 col-md-4'>
          <MemeCard :meme-info='item' />
        </div>
      </div>
    </q-infinite-scroll>
    <div class='q-pa-md q-gutter-xs flex flex-center'>
      <div class='q-gutter-md row justify-center'>
        <q-spinner-ball
          color='red'
          size='2em'
          v-if='loading'
        />
        <div v-else :style='{height: "2em"}' />
      </div>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { MemeAppRespInfo, MemeAppInfoSpec, MemeAppInfoDisplay } from 'src/stores/memeInfo'
import { ApolloClient } from '@apollo/client/core'
import gql from 'graphql-tag'
import { graphqlResult } from 'src/utils'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { LastTranscation, useUserStore, PoolTokenCond } from 'src/localstore/user'
import { useHostStore } from 'src/localstore/host'
import { POOLS } from 'src/graphql'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'

import MemeCard from './MemeCard.vue'

const user = useUserStore()
const host = useHostStore()

const limit = ref(40)
const appPoolIDsMap = ref<Map<string, string>>(new Map())
const appIDsMap = ref<Map<string, string>>(new Map())
const memeAppInfos = ref([] as MemeAppInfoDisplay[])
const lastCreatedAt = ref(0)
const curPageSize = ref(limit.value)
const loadTx = ref(true)

const getPools = async (): Promise<Array<Pool>> => {
  const options = /* await */ getClientOptions()
  const apolloClient = new ApolloClient(options)
  const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(apolloClient)(() => useQuery(POOLS, {
    endpoint: 'swap'
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

const onGetAppPools = async () => {
  const url = swapService.value
  await getPools(url)
    .then((pools) => {
      for (let i = 0; i < pools.length; i++) {
        const token0 = pools[i].token0
        const token1 = pools[i].token1
        appPoolIDsMap.value.set(token0, pools[i].id.toString())
        appPoolIDsMap.value.set(token1, pools[i].id.toString())
      }
    })
    .catch((error) => {
      console.log('getPool error: ', error)
    })
}

const getApplications = () => {
  const options = /* await */ getClientOptions()
  const apolloClient = new ApolloClient(options)
  const { /* result, refetch, fetchMore, */ onResult /*, onError */ } = provideApolloClient(apolloClient)(() => useQuery(gql`
    query getApplications($createdAfter: Int!, $limit: Int!){
      applications(createdAfter: $createdAfter, limit: $limit)
    }
  `, {
    createdAfter: lastCreatedAt.value,
    limit: limit.value
  }, {
    fetchPolicy: 'network-only'
  }))

  onResult((res) => {
    if (res.loading) return
    const apps = graphqlResult.data(res, 'applications') as Array<MemeAppRespInfo>
    for (let i = 0; i < apps.length; i++) {
      const poolId = appPoolIDsMap.value.get(apps[i].application_id)
      if (poolId === undefined || poolId === null || poolId === '') {
        continue
      }
      const checkExist = appIDsMap.value.get(apps[i].application_id)
      if (checkExist) {
        continue
      }
      appIDsMap.value.set(apps[i].application_id, apps[i].application_id)
      const parsedSpec: MemeAppInfoSpec = JSON.parse(apps[i].spec) as MemeAppInfoSpec
      const meme = {
        poolID: poolId,
        appID: apps[i].application_id,
        appName: apps[i].application_name,
        appType: apps[i].application_type,
        createdAt: apps[i].created_at,
        description: apps[i].description,
        discord: apps[i].discord,
        github: apps[i].github,
        logoStoreType: apps[i].logo_store_type,
        logo: apps[i].logo,
        telegram: apps[i].telegram,
        twitter: apps[i].twitter,
        website: apps[i].website,
        ticker: parsedSpec.ticker,
        initialSupply: parsedSpec.initial_supply,
        mintable: parsedSpec.mintable,
        poolCreated: !(poolId === undefined || poolId === null || poolId === '')
      } as MemeAppInfoDisplay
      if (apps[i].application_id === useHostStore().wlineraApplicationId) {
        meme.lastTxAt = 0
        meme.lastTxZeroAmount = '0'
        meme.lastTxOneAmount = '0'
        meme.oneDayZeroAmountVolumn = '0'
        meme.oneDayOneAmountVolumn = '0'
        meme.nowPrice = '1'
        meme.oneDayIncresePercent = '0'
      }
      memeAppInfos.value.push(meme)
      if (apps[i].created_at > lastCreatedAt.value) {
        lastCreatedAt.value = apps[i].created_at
      }
    }

    if (loadTx.value) {
      loadTxData()
      loadTx.value = false
    }
    if (memeAppInfos.value.length >= curPageSize.value) {
      runningInterval.value = false
      curPageSize.value += limit.value
      return
    }
    runningInterval.value = true
  })
}

const sleep = async (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms))
}

const onGetAppInfos = async () => {
  await onGetAppPools()
  await sleep(1000)
  getApplicationInfos(amsService.value)
}

onMounted(async () => {
  await Promise.resolve()
  if (!memeAppInfos.value?.length) {
    onLoading()
    onGetAppInfos()
      .catch((error) => {
        console.log('onGetAppInfos error: ', error)
      })
    onHiding()
  }
})

const loading = ref(false)

const onLoading = () => {
  loading.value = true
}

const onHiding = () => {
  loading.value = false
}

const onLoad = (index, done: () => void) => {
  onLoading()
  setTimeout(() => {
    loadTx.value = true
    void onGetAppInfos()
    onHiding()
    done()
  }, 30000)
}

const runningInterval = ref(true)

const useIntervalLoadData = () => {
  if (!runningInterval.value) return
  void onGetAppInfos()
}

const loadTxData = () => {
  const poolConds = [] as Array<PoolTokenCond>
  for (let i = 0; i < memeAppInfos.value.length; i++) {
    if (memeAppInfos.value[i].appID === useHostStore().wlineraApplicationId) {
      continue
    }
    const poolTokenCond = {
      PoolID: Number(memeAppInfos.value[i].poolID),
      TokenZeroAddress: memeAppInfos.value[i].appID,
      TokenOneAddress: useHostStore().wlineraApplicationId
    } as PoolTokenCond
    poolConds.push(poolTokenCond)
  }
  userStore.getLastTransactions({
    PoolTokenConds: poolConds
  }, (error: boolean, rows: LastTranscation[]) => {
    if (error) {
      return
    }
    if (rows) {
      const lastTxMap = new Map<string, LastTranscation>()
      for (let i = 0; i < rows.length; i++) {
        lastTxMap.set(rows[i].TokenZeroAddress, rows[i])
      }
      for (let i = 0; i < memeAppInfos.value.length; i++) {
        const lastTx = lastTxMap.get(memeAppInfos.value[i].appID)
        if (lastTx !== null && lastTx !== undefined) {
          memeAppInfos.value[i].lastTxAt = lastTx.LastTxAt
          memeAppInfos.value[i].lastTxZeroAmount = lastTx.LastTxZeroAmount
          memeAppInfos.value[i].lastTxOneAmount = lastTx.LastTxOneAmount
          memeAppInfos.value[i].oneDayZeroAmountVolumn = lastTx.OneDayZeroAmountVolumn
          memeAppInfos.value[i].oneDayOneAmountVolumn = lastTx.OneDayOneAmountVolumn
          memeAppInfos.value[i].nowPrice = lastTx.NowPrice
          memeAppInfos.value[i].oneDayIncresePercent = lastTx.OneDayIncresePercent
        }
      }
    }
  })
}

const interval = setInterval(useIntervalLoadData, 30 * 1000)
const txInterval = setInterval(loadTxData, 30 * 1000)

onBeforeUnmount(() => {
  clearInterval(interval)
  clearInterval(txInterval)
})

</script>

<style lang='sass' scoped>
</style>
