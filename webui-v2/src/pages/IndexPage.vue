<template>
  <q-page class='row justify-center'>
    <div class='page-width'>
      <div class='q-mt-lg'>
        <wallet-tip-view />
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
    </div>
  </q-page>
</template>

<script setup lang='ts'>

import WalletTipView from 'src/components/wallet/WalletTipView.vue'
import TradeView from 'src/components/trade/TradeView.vue'
import TrendingView from 'src/components/trending/TrendingView.vue'
import LiquidityPoolsView from 'src/components/pools/LiquidityPoolsView.vue'

</script>
