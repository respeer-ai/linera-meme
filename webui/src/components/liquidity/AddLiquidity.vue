<template>
  <AddLiquidityInner
    :next-label='$t("MSG_ADD_LIQUIDITY")'
    :token0='token0'
    :token1='token1'
    :in-page='false'
    @next='onNext'
  />
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { swap } from 'src/localstore'

import AddLiquidityInner from './AddLiquidityInner.vue'

const _swap = swap.useSwapStore()
const token0 = computed(() => _swap.selectedToken0)
const token1 = computed(() => _swap.selectedToken1)

const onNext = () => {
  // TODO: create pool by miner
}

</script>

<style scoped lang='sass'>
</style>
