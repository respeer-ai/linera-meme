<template>
  <q-page class='flex items-center justify-center'>
    <AddLiquidityInner
      :title='$t("MSG_CREATE_POOL")'
      :next-label='$t("MSG_CREATE_POOL")'
      :token0='token0'
      :token1='token1'
      :selectable='true'
      :token1-items='token1Items'
      @next='onNext'
    />
  </q-page>
</template>

<script setup lang='ts'>
import { computed, onMounted, ref, toRef, watch } from 'vue'
import { ams, meme, swap, user, proxy } from 'src/localstore'
import { constants } from 'src/constant'
import * as lineraWasm from '../../../dist/wasm/linera_wasm'
import { CREATE_POOL } from 'src/graphql'
import { stringify } from 'lossless-json'
import { useRouter } from 'vue-router'

import AddLiquidityInner from './AddLiquidityInner.vue'

interface Props {
  token0: string
  token1: string
}

// eslint-disable-next-line no-undef
const props = defineProps<Props>()
const token0 = toRef(props, 'token0')
const token1 = toRef(props, 'token1')

const _proxy = proxy.useProxyStore()

const _user = user.useUserStore()
const publicKey = computed(() => _user.publicKey)

const router = useRouter()

const onNext = async (amount0: number, amount1: number, _token1?: string) => {
  const variables = {
    token0CreatorChainId: _proxy.chain(token0.value)?.chainId as string,
    token0: token0.value,
    token1CreatorChainId: _token1 ? _proxy.chain(_token1)?.chainId as string : undefined,
    token1: _token1,
    amount0: amount0.toString(),
    amount1: amount1.toString(),
    to: undefined
  }
  const queryBytes = await lineraWasm.graphql_deserialize_swap_operation(CREATE_POOL.loc?.source?.body as string, stringify(variables) as string)
  return new Promise((resolve, reject) => {
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: constants.applicationId(constants.APPLICATION_URLS.SWAP),
        publicKey: publicKey.value,
        query: {
          query: CREATE_POOL.loc?.source?.body,
          variables,
          applicationOperationBytes: queryBytes
        },
        operationName: 'createPool'
      }
    }).then((hash) => {
      resolve(hash as string)
      void router.push({ path: '/meme' })
    }).catch((e) => {
      reject(e)
    })
  })
}

const _ams = ams.useAmsStore()
const _swap = swap.useSwapStore()

const applications = computed(() => _ams.applications)
const memeTokens = ref([] as meme.TokenItem[])

const buildTokens = () => {
  const tokens = new Map<string, meme.TokenItem>()
  applications.value.filter((el) => el.applicationType === 'Meme').forEach((el) => {
    tokens.set(el.applicationId, {
      token: el.applicationId,
      logo: _ams.applicationLogo(el),
      ticker: (JSON.parse(el?.spec || '{}') as meme.Meme).ticker,
      name: (JSON.parse(el?.spec || '{}') as meme.Meme).name
    } as meme.TokenItem)
  })
  tokens.set(constants.LINERA_NATIVE_ID, {
    token: constants.LINERA_NATIVE_ID,
    logo: constants.LINERA_LOGO,
    ticker: constants.LINERA_TICKER,
    name: 'Linera native token'
  } as meme.TokenItem)
  return Array.from(tokens.values())
}

watch(applications, () => {
  memeTokens.value = buildTokens()
}, { immediate: true, deep: true })

const token1Items = computed(() => {
  return Array.from(memeTokens.value.filter((el) => {
    if (!token0.value) return true
    return el.token !== token0.value && !_swap.existPool(el.token, token0.value)
  }))
})

onMounted(() => {
  memeTokens.value = buildTokens()
  ams.getApplications()
  swap.getPools()
})

</script>

<style scoped lang='sass'>
</style>
