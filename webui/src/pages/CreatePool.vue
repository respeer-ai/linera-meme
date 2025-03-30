<template>
  <div class='row vertical-card-align bg-grey-2 flex items-center justify-center'>
    <CreatePool :token0='token0' :token1='token1' />
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import CreatePool from 'src/components/liquidity/CreatePool.vue'

interface Query {
  token0: string
  token1: string
}

const route = useRoute()
const token0 = ref((route.query as unknown as Query).token0)
const token1 = ref((route.query as unknown as Query).token1)

</script>

<style scoped lang='sass'>
</style>
