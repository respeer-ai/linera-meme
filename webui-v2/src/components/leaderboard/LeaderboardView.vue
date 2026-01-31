<template>
  <div>
    <section-title-view icon='leaderboard' :title='`Leaderboard of ${memeTicker}`' />
    <div class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md q-mt-md'>
      <LeaderboardItemView
        v-for='(balance, index) in sortedBalances'
        :key='index'
        :data='balance'
        :ticker='memeTicker'
        :position='position(balance)'
        :application-holder='applicationHolder(balance.account)'
        :pool-holder='poolHolder(balance.account)'
        :token-value='tokenValue(balance)'
      />
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { account, ams, meme, proxy, swap } from 'src/stores/export'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'
import { constants } from 'src/constant'

import SectionTitleView from '../common/SectionTitleView.vue'
import LeaderboardItemView from './LeaderboardItemView.vue'

const tokens = computed(() => ams.Ams.applications().map((el) => {
  return {
    ...el,
    meme: JSON.parse(el.spec) as meme.Meme
  }
}))

const balances = ref({} as Record<string, string>)
const buyToken = computed(() => swap.Swap.buyToken())
const sellToken = computed(() => swap.Swap.sellToken())

const memeTokenId = computed(() => buyToken.value === constants.LINERA_NATIVE_ID ? sellToken.value : buyToken.value)
const memeToken = computed(() => tokens.value.find((el) => el.applicationId === memeTokenId.value))
const memeTicker = computed(() => memeToken.value?.meme?.ticker || constants.LINERA_TICKER)

const pool = computed(() => swap.Swap.getPool(memeTokenId.value, constants.LINERA_NATIVE_ID))
const memePrice = computed(() => (Number(memeTokenId.value === pool.value?.token0 ? pool.value?.token0Price : pool.value?.token1Price) || 0).toFixed(6))

const tokenChain = computed(() => proxy.Proxy.tokenCreatorChain(memeTokenId.value) as Chain)
const tokenApplication = computed(() => {
  return {
    chain_id: tokenChain.value?.chainId as string,
    owner: tokenChain.value?.token as string
  }
})

const applications = computed(() => ams.Ams.applications())
const applicationHolder = (account: account.Account) => {
  return applications.value.findIndex((el) => el.applicationId === account.owner) >= 0
}

const pools = computed(() => swap.Swap.pools())
const poolHolder = (account: account.Account) => {
  return pools.value.findIndex((el) => el.poolApplication.owner === account.owner) >= 0
}

const sortedBalances = computed(() =>
  Object.entries(balances.value).map(([key, value]) => ({
    account: account._Account.fromString(key),
    amount: value,
  })).filter((el) => Number(el.amount) > 0).sort((a, b) => Number(b.amount) - Number(a.amount))
)

const blockHash = computed(() => meme.MemeWrapper.blockHash(tokenApplication.value?.chain_id))

const position = (balance: { account: account.Account, amount: string }) => {
  return sortedBalances.value.filter((el) => !applicationHolder(el.account) && !poolHolder(el.account)).findIndex((el) => el.account.owner === balance.account.owner)
}

const tokenValue = (balance: { account: account.Account, amount: string }) => {
  return (Number(balance.amount) * Number(memePrice.value)).toFixed(4)
}

watch(
  tokenApplication,
  (newApp, oldApp) => {
    if (oldApp) {
      meme.MemeWrapper.finalizeMeme(oldApp.chain_id)
    }

    if (newApp) {
      meme.MemeWrapper.initializeMeme(newApp.chain_id)

      meme.MemeWrapper.balancesOfMeme(
        newApp,
        (_balances: Record<string, string>) => {
          balances.value = _balances
        }
      )
    }
  }
)

watch(blockHash, () => {
  meme.MemeWrapper.balancesOfMeme(tokenApplication.value, (_balances: Record<string, string>) => {
    balances.value = _balances
  })
})

onMounted(() => {
  if (tokenApplication.value) {
    meme.MemeWrapper.balancesOfMeme(tokenApplication.value, (_balances: Record<string, string>) => {
      balances.value = _balances
    })
    meme.MemeWrapper.initializeMeme(tokenApplication.value.chain_id)
  }
})

onUnmounted(() => {
  if (tokenApplication.value) {
    meme.MemeWrapper.finalizeMeme(tokenApplication.value.chain_id)
  }
})

</script>
