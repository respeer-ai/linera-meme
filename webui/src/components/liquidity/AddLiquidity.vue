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
import { swap, pool, account, user } from 'src/localstore'
import * as lineraWasm from '../../../dist/wasm/linera_wasm'
import { ADD_LIQUIDITY } from 'src/graphql'
import { stringify } from 'lossless-json'

import AddLiquidityInner from './AddLiquidityInner.vue'

const _swap = swap.useSwapStore()
const _user = user.useUserStore()

const publicKey = computed(() => _user.publicKey)

const poolApplication = computed(() => _swap.selectedPool?.poolApplication)
const token0 = computed(() => _swap.selectedToken0)
const token1 = computed(() => _swap.selectedToken1)

const onNext = async (amount0: number, amount1: number) => {
  const variables = {
    amount0In: amount0.toString(),
    amount1In: amount1.toString(),
    amount0OutMin: undefined,
    amount1OutMin: undefined,
    to: undefined,
    blockTimestamp: undefined
  }
  const queryBytes = await lineraWasm.graphql_deserialize_pool_operation(ADD_LIQUIDITY.loc?.source?.body as string, stringify(variables) as string)
  return new Promise((resolve, reject) => {
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: account._Account.accountOwner(poolApplication.value),
        publicKey: publicKey.value,
        query: {
          query: ADD_LIQUIDITY.loc?.source?.body,
          variables,
          applicationOperationBytes: queryBytes
        },
        operationName: 'addLiquidity'
      }
    }).then((hash) => {
      resolve(hash as string)
    }).catch((e) => {
      reject(e)
    })
  })
}

</script>

<style scoped lang='sass'>
</style>
