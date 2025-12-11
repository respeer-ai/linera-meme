<template>
  <div class='cursor-pointer row'>
    <div class='bg-primary-25 hover-primary radius-8 flex justify-center items-center' style='width: 48px; height: 48px;'>
    <q-img :src='laughPng' width='36px' height='36px' />
    </div>
    <div :class='[ "q-ml-sm", showSubtitle ? "" : "flex justify-center" ]'>
      <div class='text-light text-h5 text-bold text-gradient-primary-secondary flex items-center'> {{ productName }} </div>
      <div v-if='showSubtitle' class='text-xs text-neutral' style='line-height: 1em;'>Creating . Trading . Mining Meme on Linera</div>
    </div>
</div>
</template>

<script setup lang='ts'>
import { toRef } from 'vue'

import { laughPng } from 'src/assets'

interface Props {
  showSubtitle?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  showSubtitle: true
})
const showSubtitle = toRef(props, 'showSubtitle')

const productName = import.meta.env.VITE_PRODUCT_NAME || import.meta.env.PRODUCT_NAME

</script>
