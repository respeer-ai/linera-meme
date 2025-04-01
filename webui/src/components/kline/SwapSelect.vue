<template>
  <div class='bg-white vertical-card-padding'>
    <q-select
      dense outlined hide-dropdown-icon
      v-model='token0' :options='token0Items'
      class='swap-token-option'
    >
      <template #option='scope'>
        <q-item dense v-bind='scope.itemProps'>
          <q-img :src='scope.opt.logo' width='24px' height='24px' fit='contain' />
          <div class='horizontal-inner-x-margin-left'>
            <div class='row'>
              <div class='swap-token-name text-bold'>
                {{ scope.opt.ticker }}
              </div>
              <q-space />
            </div>
            <div>{{ scope.opt.name }}</div>
          </div>
        </q-item>
      </template>
      <template #selected>
        <div class='row'>
          <q-img :src='token0?.logo' width='24px' height='24px' fit='contain' />
          <div class='swap-token-name text-bold swap-token-label flex items-center justify-center'>
            {{ token0?.ticker }}
          </div>
        </div>
      </template>
    </q-select>
    <div class='separator'>
      /
    </div>
    <q-select
      dense outlined hide-dropdown-icon
      v-model='token1' :options='token1Items'
      class='swap-token-option'
    >
      <template #option='scope'>
        <q-item dense v-bind='scope.itemProps'>
          <q-img :src='scope.opt.logo' width='24px' height='24px' fit='contain' />
          <div class='horizontal-inner-x-margin-left'>
            <div class='row'>
              <div class='swap-token-name text-bold'>
                {{ scope.opt.ticker }}
              </div>
              <q-space />
            </div>
            <div>{{ scope.opt.name }}</div>
          </div>
        </q-item>
      </template>
      <template #selected>
        <div class='row'>
          <q-img :src='token1?.logo' width='24px' height='24px' fit='contain' />
          <div class='swap-token-name text-bold swap-token-label flex items-center justify-center'>
            {{ token1?.ticker }}
          </div>
        </div>
      </template>
    </q-select>
  </div>
</template>

<script setup lang='ts'>
import { swap, ams, meme } from 'src/localstore'
import { computed, ref, watch } from 'vue'
import { constants } from 'src/constant'
import { Pool } from 'src/__generated__/graphql/swap/graphql'

const _swap = swap.useSwapStore()
const _ams = ams.useAmsStore()

const pools = computed(() => _swap.pools)
const applications = computed(() => _ams.applications)
const poolTokens = ref([] as meme.TokenItem[])
const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)

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

const token0Items = computed(() => {
  return Array.from(poolTokens.value.values().filter((el) => _swap.existTokenPool(el.token)))
})
const token1Items = computed(() => {
  return Array.from(poolTokens.value.values().filter((el) => {
    if (!token0.value) return true
    return el.token !== token0.value?.token && _swap.existPool(el.token, token0.value?.token)
  }))
})

const token0 = ref(undefined as unknown as meme.TokenItem)
const token1 = ref(undefined as unknown as meme.TokenItem)

watch(selectedToken0, () => {
  token0.value = poolTokens.value.find((el) => el.token === selectedToken0.value) as meme.TokenItem
})

watch(selectedToken1, () => {
  token1.value = poolTokens.value.find((el) => el.token === selectedToken1.value) as meme.TokenItem
})

watch(token0Items, () => {
  if (!token0.value?.logo || !token0.value?.name || !token0.value?.ticker || !token0.value?.token) token0.value = token0Items.value[0]
}, { immediate: true, deep: true })

watch(token0, () => {
  if (!token0.value) return
  if (!_swap.existPool(token0.value.token, token1.value?.token)) {
    token1.value = token1Items.value[0]
  }
  if (token0.value && token1.value) {
    _swap.selectedPool = _swap.getPool(token0.value.token, token1.value.token) as Pool
    _swap.selectedToken0 = token0.value.token
    _swap.selectedToken1 = token1.value.token
  }
}, { immediate: true, deep: true })

watch(applications, () => {
  poolTokens.value = buildTokens()
}, { immediate: true, deep: true })

watch(pools, () => {
  poolTokens.value = buildTokens()
}, { immediate: true, deep: true })

</script>

<style scoped lang='sass'>
.swap-token-name
  line-height: 26px

:deep(.swap-token)
  .q-select
    .q-icon
      font-size: 16px

.swap-token-option
  display: inline-block
  border-radius: 4px

.swap-token-label
  margin-left: 8px
  overflow: hidden

.separator
  display: inline-block
  font-size: 24px
  margin-left: 8px
  margin-right: 8px
  font-weight: bolder
  color: #aaa
</style>
