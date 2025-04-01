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
import { computed, onMounted, ref, toRef } from 'vue'
import { ams, meme, swap } from 'src/localstore'
import { constants } from 'src/constant'

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

const _ams = ams.useAmsStore()
const _swap = swap.useSwapStore()

const pools = computed(() => _swap.pools)
const poolTokens = ref([] as meme.TokenItem[])

const buildTokens = () => {
  const tokens = new Map<string, meme.TokenItem>()
  pools.value.forEach((el) => {
    const application = _ams.application(el.token0 as string) as ams.Application
    tokens.set(el.token0 as string, {
      token: el.token0 as string,
      logo: _ams.applicationLogo(application),
      ticker: (JSON.parse(application?.spec || '{}') as meme.Meme).ticker,
      name: (JSON.parse(application?.spec || '{}') as meme.Meme).name
    } as meme.TokenItem)
    // Native token
    if (el.token1 === constants.LINERA_TICKER) {
      tokens.set(constants.LINERA_NATIVE_ID, {
        token: constants.LINERA_NATIVE_ID,
        logo: constants.LINERA_LOGO,
        ticker: constants.LINERA_TICKER,
        name: 'Linera native token'
      } as meme.TokenItem)
    } else {
      const application = _ams.application(el.token1 as string) as ams.Application
      tokens.set(el.token1 as string, {
        token: el.token1 as string,
        logo: _ams.applicationLogo(application),
        ticker: (JSON.parse(application?.spec || '{}') as meme.Meme).ticker,
        name: (JSON.parse(application?.spec || '{}') as meme.Meme).name
      } as meme.TokenItem)
    }
  })
  return Array.from(tokens.values())
}

const token1Items = computed(() => {
  return Array.from(poolTokens.value.values().filter((el) => {
    if (!token0.value) return true
    return el.token !== token0.value && _swap.existPool(el.token, token0.value)
  }))
})

onMounted(() => {
  poolTokens.value = buildTokens()
})

</script>

<style scoped lang='sass'>
</style>
