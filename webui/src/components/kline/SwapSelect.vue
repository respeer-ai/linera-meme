<template>
  <div class='bg-white vertical-card-padding'>
    <q-select
      dense v-model='token0' :options='[]' hide-dropdown-icon
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
          <q-img :src='processImg("AAAAA", "BBBBB")' width='24px' height='24px' fit='contain' />
          <div class='swap-token-name text-bold swap-token-label flex items-center justify-center'>
            AAAAAAA
          </div>
        </div>
      </template>
    </q-select>
    <div class='separator'>
      /
    </div>
    <q-select
      dense v-model='tokenPair' :options='[]' hide-dropdown-icon
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
          <q-img :src='processImg("AAAAA", "BBBBB")' width='24px' height='24px' fit='contain' />
          <div class='swap-token-name text-bold swap-token-label flex items-center justify-center'>
            AAAAAA
          </div>
        </div>
      </template>
    </q-select>
  </div>
</template>

<script setup lang='ts'>
import { shortid } from 'src/utils'
import { blob, store } from 'src/localstore'
import { ref } from 'vue'

const token0 = ref(undefined as unknown)
const tokenPair = ref(undefined as unknown)

const processImg = (storeType: string | undefined, imageHash: string | undefined): string => {
  if (storeType === undefined || imageHash === undefined) {
    return ''
  }
  return blob.BlobGateway.imagePath(storeType as store.StoreType, imageHash)
}

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
