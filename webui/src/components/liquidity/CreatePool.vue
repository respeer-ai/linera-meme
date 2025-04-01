<template>
  <q-page class='flex items-center justify-center'>
    <AddLiquidityInner
      :title='$t("MSG_CREATE_POOL")'
      :next-label='$t("MSG_CREATE_POOL")'
      :token0='token0'
      :token1='token1'
      @next='onNext'
    />
  </q-page>
</template>

<script setup lang='ts'>
import { toRef } from 'vue'

import AddLiquidityInner from './AddLiquidityInner.vue'

interface Props {
  token0: string
  token1: string
}

// eslint-disable-next-line no-undef
const props = defineProps<Props>()
const token0 = toRef(props, 'token0')
const token1 = toRef(props, 'token1')

const onNext = () => {
  // TODO: create pool by miner
}

</script>

<style scoped lang='sass'>
</style>
