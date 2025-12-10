<template>
  <div class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md'>
    <div class='row'>
      <div class='font-size-16 text-bold'>{{ action }}</div>
      <q-space />
      <q-select
        :options='tokens'
        v-model='token'
        class='bg-primary-twenty-five radius-16'
      >
        <template #prepend>
          <q-avatar>
            <q-img :src='token?.image' size='24px' />
          </q-avatar>
        </template>
      </q-select>
    </div>
    <div class='q-mt-lg row items-end'>
      <q-input v-model='amount' type='number' class='font-size-36 text-neutral text-bold' placeholder='0' :autofocus='autoFocus' style='max-width: 120px;' />
      <q-space />
      <div class='font-size-20 text-neutral'>$ 0</div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { onMounted, ref, toRef } from 'vue'
import { TokenAction } from './TokenAction'
import { Token } from './Token'

interface Props {
  action?: TokenAction
  autoFocus?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  action: TokenAction.Sell,
  autoFocus: true
})
const action = toRef(props, 'action')
const autoFocus = toRef(props, 'autoFocus')

const amount = ref('')

interface TokenItem extends Token {
  label: string
  value: string
}

const tokens = ref([{
    label: 'TLINERA',
    value: 'TLINERA',
    image: 'https://avatars.githubusercontent.com/u/107513858?s=48&v=4',
    ticker: 'TLINERA'
  }, {
    label: 'LTTM',
    value: 'LTTM',
    image: 'info',
    ticker: 'LTTM'
  }, {
    label: 'LTFT',
    value: 'LTFT',
    image: 'info',
    ticker: 'LTFT'
  }, {
    label: 'GMIC',
    value: 'GMIC',
    image: 'info',
    ticker: 'GMIC'
  }
] as TokenItem[])

const token = defineModel<Token>()

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
</style>
