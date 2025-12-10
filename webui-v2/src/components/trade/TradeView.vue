<template>
  <div class='row content-start wrap'>
    <div class='trade-action'>
      <div class='row items-center'>
        <token-input-view :action='TokenAction.Sell' style='width: calc(50% - 4px);' v-model='sellToken' />
        <div class='radius-24 bg-accent q-pa-sm cursor-pointer hover-primary' style='height: 48px; width: 48px; margin-left: -20px; z-index: 1000;'>
          <q-icon name='arrow_forward' size='32px' />
        </div>
        <token-input-view :action='TokenAction.Buy' style='width: calc(50% - 4px); margin-left: -20px;' :auto-focus='false' v-model='buyToken' />
      </div>
      <q-card flat class='q-pa-md q-mt-md border-dark-secondary radius-8 bg-dark-secondary'>
        <div>
          <div class='row'>
            <span class='font-size-18 text-bold text-neutral'>Price Chart</span>
          </div>
        </div>
      </q-card>
    </div>

    <q-card flat class='q-pa-md flex-grow selected-token-info border-dark-secondary radius-8 bg-dark-secondary'>
      <TokenInfoView :token='buyToken' />
    </q-card>
  </div>
</template>

<script setup lang='ts'>
import { TokenAction } from './TokenAction'
import { Token } from './Token'
import { ref } from 'vue'

import TokenInputView from './TokenInputView.vue'
import TokenInfoView from './TokenInfoView.vue'

const buyToken = ref(undefined as unknown as Token)
const sellToken = ref(undefined as unknown as Token)

</script>

<style scoped lang='sass'>
.trade-action
  width: 768px

.selected-token-info
  width: calc(100% - 768px - 16px)
  margin-left: 16px

@media (max-width: 960px)
  .trade-action
    width: 100%

  .selected-token-info
    width: 100%
    margin-left: 0
    margin-top: 16px
</style>