<template>
  <div class='row' :style='{ borderBottom: underline ? "1px solid var(--q-dark)" : "", paddingBottom: underline ? "12px" : "0", lineHeight: "24px" }'>
    <div class='text-neutral'>{{ label }}</div>
    <q-space />
    <div v-if='logo?.length'>
      <q-img :src='logo' width='24px' height='24px' />
    </div>
    <div :style='{ color: valueColorVar }' :class='[ "q-ml-sm", valueBold ? "text-bold" : "" ]' v-html='value' />
  </div>
</template>

<script setup lang='ts'>
import { computed, toRef } from 'vue'

interface Props {
  logo?: string
  label: string
  value: string
  valueColor: string
  valueBold: boolean
  underline: boolean
}
const props = defineProps<Props>()
const logo = toRef(props, 'logo')
const label = toRef(props, 'label')
const value = toRef(props, 'value')
const valueColor = toRef(props, 'valueColor')
const valueBold = toRef(props, 'valueBold')
const underline = toRef(props, 'underline')

const valueColorVar = computed(() => `var(--q-${valueColor.value})`)

</script>
