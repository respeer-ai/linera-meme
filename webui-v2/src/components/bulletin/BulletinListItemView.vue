<template>
  <div class='row border-grey-10 radius-8 items-center q-pa-sm cursor-pointer hover-move'>
    <q-avatar :style='{ border: `1px solid ${imageBorderColor}` }'>
      <q-img :src='data.image' width='36px' height='36px' />
    </q-avatar>
    <div class='q-ml-md' style='width: calc((100% - 48px - 32px) * 0.5);'>
      <div class='text-light font-size-20'>$ {{ data.label }}</div>
      <div class='text-neutral font-size-16'>{{ data.subtitle }}</div>
    </div>
    <q-space />
    <div class='q-ml-md text-right'  style='width: calc((100% - 48px - 32px) * 0.5);'>
      <div :style='{ color: valueColor }'>{{ data.value }} TLINERA</div>
      <div :style='{ color: captionColor }'>{{ data.caption }}</div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, toRef } from 'vue'
import { BulletinItem } from './BulletinItem'

interface Props {
  data: BulletinItem
}
const props = defineProps<Props>()
const data = toRef(props, 'data')

const imageBorderColor = computed(() => `var(--q-${data.value.imageBorderColor})`)
const valueColor = computed(() => `var(--q-${data.value.valueColor})`)
const captionColor = computed(() => `var(--q-${data.value.captionColor})`)

</script>
