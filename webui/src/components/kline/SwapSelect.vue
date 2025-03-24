<template>
  <div class='bg-white vertical-card-padding'>
    <q-select
      dense v-model='swapStore.SelectedToken' :options='swapStore.Tokens' hide-dropdown-icon
      class='swap-token-option'
    >
      <template #option='scope'>
        <q-item dense v-bind='scope.itemProps'>
          <q-img :src='processImg(scope.opt.IconStoreType, scope.opt.Icon)' width='24px' height='24px' fit='contain' />
          <div class='swap-token-list horizontal-inner-x-margin-left'>
            <div class='row'>
              <div class='swap-token-name text-bold'>
                {{ scope.opt.Symbol }}
              </div>
              <q-space />
            </div>
            <div>{{ shortid.shortId(scope.opt.Name, 10) }}</div>
          </div>
        </q-item>
      </template>
      <template #selected>
        <div class='row'>
          <q-img :src='processImg(swapStore.SelectedToken?.IconStoreType, swapStore.SelectedToken?.Icon)' width='24px' height='24px' fit='contain' />
          <div class='swap-token-name text-bold swap-token-label flex items-center justify-center'>
            {{ swapStore.SelectedToken?.Symbol }}
          </div>
        </div>
      </template>
    </q-select>
    <div class='separator'>
      /
    </div>
    <q-select
      dense v-model='swapStore.SelectedTokenPair' :options='swapStore.TokenPairs' hide-dropdown-icon
      class='swap-token-option'
    >
      <template #option='scope'>
        <q-item dense v-bind='scope.itemProps'>
          <q-img :src='processImg(scope.opt.TokenOneIconStoreType, scope.opt.TokenOneIcon)' width='24px' height='24px' fit='contain' />
          <div class='swap-token-list horizontal-inner-x-margin-left'>
            <div class='row'>
              <div class='swap-token-name text-bold'>
                {{ scope.opt.TokenOneSymbol }}
              </div>
              <q-space />
            </div>
            <div>{{ shortid.shortId(scope.opt.TokenOneName, 10) }}</div>
          </div>
        </q-item>
      </template>
      <template #selected>
        <div class='row'>
          <q-img :src='processImg(swapStore.SelectedTokenPair?.TokenOneIconStoreType, swapStore.SelectedTokenPair?.TokenOneIcon)' width='24px' height='24px' fit='contain' />
          <div class='swap-token-name text-bold swap-token-label flex items-center justify-center'>
            {{ swapStore.SelectedTokenPair?.TokenOneSymbol }}
          </div>
        </div>
      </template>
    </q-select>
  </div>
</template>

<script setup lang='ts'>
import { useHostStore } from 'src/mystore/host'
import { useSwapStore } from 'src/mystore/swap'
import { shortid } from 'src/utils'
import { computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

const swapStore = useSwapStore()

const router = useRouter()
const t0Addr = router.currentRoute.value.query.token0
const t1Addr = router.currentRoute.value.query.token1

const selectedToken = computed(() => swapStore.SelectedToken)

const processImg = (storeType: string | undefined, imageHash: string | undefined): string => {
  if (storeType === undefined || imageHash === undefined) {
    return ''
  }
  return useHostStore().blobDataPath(storeType, imageHash)
}

const getTokenPairs = () => {
  if (!swapStore.SelectedToken) {
    swapStore.SelectedTokenPair = null
    return
  }
  swapStore.getTokenPairsByTokenZeroID((error) => {
    if (error) return
    if (swapStore.TokenPairs.length === 0) {
      swapStore.SelectedTokenPair = null
      return
    }

    const _t0Addr = t0Addr || selectedToken.value?.Address
    const _t1Addr = t1Addr || useHostStore().wlineraApplicationId

    if (_t0Addr) {
      for (const info of swapStore.TokenPairs) {
        if (_t0Addr !== info.TokenZeroAddress && _t0Addr !== info.TokenOneAddress) {
          continue
        }
        if (_t1Addr !== info.TokenZeroAddress && _t1Addr !== info.TokenOneAddress) {
          continue
        }
        swapStore.SelectedTokenPair = info
        return
      }
    }

    if (!swapStore.SelectedTokenPair) {
      swapStore.SelectedTokenPair = swapStore.TokenPairs[0]
    }
  })
}

watch(selectedToken, () => {
  getTokenPairs()
})

const refreshTokens = () => {
  swapStore.getTokens((error) => {
    if (error) return
    if (swapStore.Tokens.length === 0) {
      swapStore.SelectedToken = null
      return
    }
    const _t0Addr = t0Addr || selectedToken.value?.Address
    if (_t0Addr) {
      for (const info of swapStore.Tokens) {
        if (_t0Addr && _t0Addr === info.Address) {
          swapStore.SelectedToken = info
          getTokenPairs()
          return
        }
      }
    }

    if (!swapStore.SelectedToken) {
      swapStore.SelectedToken = swapStore.Tokens[0]
      getTokenPairs()
    }
  })
}

onMounted(() => {
  refreshTokens()
})

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
  margin-left: 15px
  margin-right: 15px
  font-weight: bolder
  color: #aaa
</style>
