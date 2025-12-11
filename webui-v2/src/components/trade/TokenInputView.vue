<template>
  <div class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md'>
    <div class='row'>
      <div class='font-size-16 text-bold'>{{ action }}</div>
      <q-space />
      <q-select
        :options='_tokens'
        v-model='token'
        class='bg-primary-twenty-five radius-16'
        style='overflow: hidden;'
      >
        <template #option='scope'>
          <q-item dense v-bind='scope.itemProps' class='items-center'>
            <q-avatar size='24px'>
              <q-img :src='ams.applicationLogo(scope.opt as ams.Application) || constants.LINERA_LOGO' width='24px' height='24px' fit='contain' />
            </q-avatar>
            <div class='q-ml-md'>
              <div class='row'>
                <div class='text-neutral text-bold'>
                  {{ scope.opt.meme?.ticker }}
                </div>
                <q-space />
              </div>
            </div>
          </q-item>
        </template>
        <template #selected>
          <div class='row'>
            <q-avatar size='24px' class='q-ml-xs'>
              <q-img :src='tokenLogo' width='24px' height='24px' fit='contain' />
            </q-avatar>
            <div class='swap-token-name text-bold swap-token-label flex items-center justify-center q-ml-sm'>
              {{ tokenTicker }}
            </div>
          </div>
        </template>
      </q-select>
    </div>
    <q-input v-model='amount' type='number' class='font-size-36 text-neutral text-bold' placeholder='0' :autofocus='autoFocus' />
    <div class='q-mt-sm row'>
      <div class='font-size-16 text-neutral'>$ 0</div>
      <q-space />
      <div class='font-size-16 text-neutral'>0.1234 {{ token?.meme?.ticker }}</div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted, ref, toRef } from 'vue'
import { TokenAction } from './TokenAction'
import { Token } from './Token'
import { ams } from 'src/stores/export'
import { constants } from 'src/constant'

interface Props {
  action?: TokenAction
  autoFocus?: boolean
  tokens: Token[]
}
const props = withDefaults(defineProps<Props>(), {
  action: TokenAction.Sell,
  autoFocus: true
})
const action = toRef(props, 'action')
const autoFocus = toRef(props, 'autoFocus')
const tokens = toRef(props, 'tokens')

const amount = ref('')

interface TokenItem extends Token {
  label: string
  value: string
}
const _tokens = computed(() => tokens.value.map((el) => {
  return  {
    ...el,
    label: el.meme.ticker,
    value: el.meme.ticker
  } as TokenItem
}))

const token = defineModel<Token>()
const tokenLogo = computed(() => ams.applicationLogo(token.value as ams.Application) || constants.LINERA_LOGO)
const tokenTicker = computed(() => token.value?.meme?.ticker || constants.LINERA_TICKER)

onMounted(() => {
  token.value = tokens.value[0]
})

</script>

<style scoped lang='sass'>
::v-deep(.q-input)
  .q-field__native,
  .q-field__control
    border-radius: 0
  .q-field__control:hover
    background-color: none !important
    background: none !important

::v-deep(.q-select)
  line-height: 32px
  .q-field__marginal
    height: 32px
  .q-field--auto-height
    min-height: 32px
  .q-field__control
    min-height: 32px
    height: 32px
  .q-field__native
    min-height: 32px
    padding: 0
</style>
