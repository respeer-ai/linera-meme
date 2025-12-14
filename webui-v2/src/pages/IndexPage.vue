<template>
  <q-page class='row justify-center'>
    <div class='page-width'>
      <div v-if='!walletConnected' class='q-mt-lg'>
        <wallet-tip-view />
      </div>
      <div class='q-mt-lg'>
        <search-view />
      </div>
      <div class='q-mt-lg'>
        <trade-view />
      </div>
      <div class='q-mt-xl'>
        <trending-view />
      </div>
      <div class='q-mt-xl'>
        <liquidity-pools-view />
      </div>
      <div class='q-mt-xl'>
        <leaderboard-view />
      </div>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
  import { computed } from 'vue'
  import { user } from 'src/stores/export'

import WalletTipView from 'src/components/wallet/WalletTipView.vue'
import TradeView from 'src/components/trade/TradeView.vue'
import TrendingView from 'src/components/trending/TrendingView.vue'
import LiquidityPoolsView from 'src/components/pools/LiquidityPoolsView.vue'
import LeaderboardView from 'src/components/leaderboard/LeaderboardView.vue'
import SearchView from 'src/components/search/SearchView.vue'

const walletConnected = computed(() => user.User.walletConnected())

</script>
