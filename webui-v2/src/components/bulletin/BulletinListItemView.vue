<template>
  <div>{{ data }}</div>
</template>

<script setup lang='ts'>
import { toRef } from 'vue'
import { BulletinItem } from './BulletinItem'

interface Props {
  data: BulletinItem
}
const props = defineProps<Props>()
const data = toRef(props, 'data')

</script>
