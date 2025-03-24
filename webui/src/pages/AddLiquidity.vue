<template>
  <div class='row vertical-card-align bg-grey-2 flex items-center justify-center'>
    <AddTokenLiquidity :token0-id='token0Id' :token0-ticker='token0Ticker' />
  </div>
</template>

<script setup lang='ts'>
import { defineAsyncComponent, ref } from 'vue'
import { useRoute } from 'vue-router'

interface Query {
  token0Id: string
  token0Ticker: string
}

const AddTokenLiquidity = defineAsyncComponent(() => import('src/components/liquidity/AddTokenLiquidity.vue'))

const route = useRoute()
const token0Id = ref((route.query as unknown as Query).token0Id)
const token0Ticker = ref((route.query as unknown as Query).token0Ticker)

</script>

<style scoped lang='sass'>
</style>
