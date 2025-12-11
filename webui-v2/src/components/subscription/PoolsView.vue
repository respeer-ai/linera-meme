<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { swap } from 'src/stores/export'
import { onMounted } from 'vue'

// TODO: subscription pools

onMounted(() => {
  swap.getPools()
})

</script>
