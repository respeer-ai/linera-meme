<template>
  <div class='q-px-lg'>
    <div class='text-neutral font-size-20'>Swap slippage tolerance</div>
    <q-separator class='q-mt-sm' color='nautral' />

    <div class='row q-mt-lg items-center text-neutral'>
      <div
        v-for='_slippage in slippages'
        :key='_slippage'
        :class='[ "bg-accent q-px-md q-py-xs q-mr-sm radius-16 text-bold cursor-pointer hover-primary", _slippage === slippage ? "border-secondary-25" : "" ]'
        @click='onSlippageClick(_slippage)'
      >
        {{ _slippage }}%
      </div>
      <q-space />
      <div class='row' style='max-width: 128px;'>
        <q-input filled v-model='slippage' class='font-size-16 text-neutral text-bold' input-class='text-right' suffix='%' />
      </div>
    </div>

    <div class='q-mt-lg'>
      <q-btn no-caps rounded class='fill-parent-width bg-primary font-size-20' @click='onSaveClick'>
        Save
      </q-btn>
      <q-btn no-caps rounded class='fill-parent-width border-primary-50 q-mt-sm font-size-20' @click='onCancelClick'>
        Cancel
      </q-btn>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { defaultSlippage, slippages } from './Slippages'

const slippage = defineModel({ default: defaultSlippage })

const emit = defineEmits<{
  (e: 'done', slippage: number): void,
  (e: 'cancel'): void
}>()

const onSlippageClick = (_slippage: number) => {
  slippage.value = _slippage
}

const onSaveClick = async () => {
  emit('done', slippage.value)
}

const onCancelClick = () => {
  emit('cancel')
}

</script>

<style scoped lang='sass'>
::v-deep(.q-input)
  .q-field__control,
  .q-field__native
    min-height: 32px
    height: 32px
  .q-field__suffix
    line-height: 24px
</style>
