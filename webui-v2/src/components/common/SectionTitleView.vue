<template>
  <div>
    <div class='row items-center q-section-title-line'>
      <q-icon :name='icon' class='text-primary' size='24px' />
      <div class='font-size-24 q-ml-sm'>{{ title }}</div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { toRef } from 'vue'

interface Props {
  icon: string
  title: string
}
const props = defineProps<Props>()
const icon = toRef(props, 'icon')
const title = toRef(props, 'title')

</script>
