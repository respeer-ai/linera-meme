<template>
  <div>{{ token }}</div>
</template>

<script setup lang='ts'>
import { toRef } from 'vue'
import { Token } from './Token'

interface Props {
  token: Token
}
const props = defineProps<Props>()
const token = toRef(props, 'token')

</script>
