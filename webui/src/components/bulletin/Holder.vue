<template>
  <div>
    <div>
      <strong>Treasure leaderboard</strong>
    </div>
    <q-separator />
    <div v-for='(item, index) in topList' :key='item.owner.chain_id' class='row decorate-dashed-border-bottom vertical-inner-y-margin'>
      <q-img
        v-if='index === 0'
        :src='trophyNo1' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='index === 1'
        :src='trophyNo2' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='index === 2'
        :src='trophyNo3' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='index > 2'
        src='' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <div>{{ shortId(item.owner.owner, 8) }}</div>
      <q-space />
      <div>{{ Number(item.balance).toFixed(2) }} {{ selectedToken?.Symbol }}</div>
    </div>
  </div>
</template>
<script setup lang='ts'>
import { onMounted, ref, watch, computed } from 'vue'
import gql from 'graphql-tag'
import { useRouter } from 'vue-router'
import { ApolloClient } from '@apollo/client/core'
import { graphqlResult } from 'src/utils'
import { getAppClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { OwnerBalance } from 'src/stores/memeInfo'
import { trophyNo1, trophyNo2, trophyNo3 } from 'src/assets'
import { useSwapStore } from 'src/mystore/swap'
import { shortId } from 'src/utils/shortid'
import { useHostStore } from 'src/mystore/host'

const router = useRouter()
const swapStore = useSwapStore()

const topList = ref([] as Array<OwnerBalance>)
const selectedToken = computed(() => swapStore.SelectedToken)

const token0 = ref('')

watch(selectedToken, (selected) => {
  if (!selected) {
    token0.value = ''
    topList.value = []
    return
  }
  token0.value = selectedToken.value?.Address as string
  void getBalanceTopList(10)
})

onMounted(() => {
  if (router.currentRoute.value.query.token0 != null) {
    token0.value = router.currentRoute.value.query.token0 as string
    void getBalanceTopList(10)
  }
})

const getBalanceTopList = (limit: number) => {
  const url = useHostStore().swapApplicationTokenPath(token0.value)
  const appOptions = /* await */ getAppClientOptions(url)
  const appApolloClient = new ApolloClient(appOptions)
  const { /* result, refetch, fetchMore, */ onResult /*, onError */ } = provideApolloClient(appApolloClient)(() => useQuery(gql`
    query balanceTopList($limit: Int!) {
      balanceTopList(limit: $limit) {
        owner,
        balance
      }
    }
  `, {
    chainId: useHostStore().swapCreationChainId,
    limit: limit
  }, {
    fetchPolicy: 'network-only'
  }))

  onResult((res) => {
    if (res.loading) return
    const ownerBalances = graphqlResult.data(res, 'balanceTopList') as Array<OwnerBalance>
    topList.value = ownerBalances || []
  })
}

</script>
