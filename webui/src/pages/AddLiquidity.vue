<template>
  <div class='row vertical-card-align bg-grey-2 flex items-center justify-center'>
    <AddTokenLiquidity :token0-id='token0Id' :token0-ticker='token0Ticker' />
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import AddTokenLiquidity from 'src/components/liquidity/AddTokenLiquidity.vue'

interface Query {
  token0Id: string
  token0Ticker: string
}

const route = useRoute()
const token0Id = ref((route.query as unknown as Query).token0Id)
const token0Ticker = ref((route.query as unknown as Query).token0Ticker)

</script>

<style scoped lang='sass'>
</style>
