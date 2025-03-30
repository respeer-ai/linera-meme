<template>
  <div class='bg-white popup-padding'>
    <h5>Create pool</h5>
    <q-separator />
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            {{ token0Ticker }}
          </div>
          <div class='text-grey-8'>
            {{ shortId(token0 || '', 5) }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(outBalance).toFixed(2) }}
          </div>
          <div class='text-grey-8'>
            {{ token0Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          class='swap-amount-input text-grey-8' dense v-model.number='token0Amount' reverse-fill-mask
          input-class='text-right'
          :error='token0AmountError'
        />
      </div>
    </q-card>
    <div class='row vertical-card-align'>
      <div class='decorate-border-bottom-bold exchange-separator' />
      <div class='exchange-symbol' size='28px'>
        <q-icon name='bi-three-dots' size='14px' class='text-grey-6' />
      </div>
      <div class='decorate-border-bottom-bold exchange-separator' />
    </div>
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-card-align'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            {{ token1Ticker }}
          </div>
          <div class='text-grey-8'>
            {{ shortId(token1 || '', 5) }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(inBalance).toFixed(2) }}
          </div>
          <div class='text-grey-8'>
            {{ token1Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          class='swap-amount-input' dense v-model.number='token1Amount' reverse-fill-mask
          input-class='text-right'
          :error='token1AmountError'
        />
      </div>
    </q-card>
    <q-btn
      rounded flat :label='$t("MSG_ADD_LIQUIDITY")' class='full-width border-red-4 vertical-inner-y-margin vertical-inner-y-margin-bottom'
    />
  </div>
</template>

<script setup lang='ts'>
import { shortId } from 'src/utils/shortid'
import { ref, watch, onMounted, toRef, computed } from 'vue'
import { ams, meme } from 'src/localstore'

interface Props {
  token0: string
  token1: string
}

// eslint-disable-next-line no-undef
const props = defineProps<Props>()
const token0 = toRef(props, 'token0')
const token1 = toRef(props, 'token1')

const _ams = ams.useAmsStore()

const token0Ticker = computed(() => (JSON.parse(_ams.application(token0.value)?.spec || '{}') as meme.Meme).ticker)
const token1Ticker = computed(() => (JSON.parse(_ams.application(token1.value)?.spec || '{}') as meme.Meme).ticker)

const token0Amount = ref(0)
const token1Amount = ref(0)

const token0AmountError = ref(false)
const token1AmountError = ref(false)

const outBalance = ref(0)
const inBalance = ref(0)

watch(token0Amount, () => {
  token0Amount.value = token0Amount.value < 0 ? 0 : token0Amount.value
})

watch(token1Amount, (amount) => {
  token1Amount.value = token1Amount.value < 0 ? 0 : token1Amount.value
})

const getApplications = () => {
  ams.getApplications((error: boolean, rows?: ams.Application[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

onMounted(() => {
  getApplications()
})

</script>

<style scoped lang='sass'>
.swap-amount-label
  font-size: 20px
  margin-right: 4px

.swap-amount-icon
  margin-right: 4px
  margin-top: 2px

:deep(.swap-token)
  .q-select
    .q-icon
      font-size: 16px

.swap-amount-input
  width: 100%

.exchange-symbol
  border: 2px solid $grey-4
  border-radius: 50%
  width: 28px
  height: 28px
  padding: 2px 5px

.exchange-separator
  width: calc(50% - 14px)
  margin-bottom: 12px
</style>
