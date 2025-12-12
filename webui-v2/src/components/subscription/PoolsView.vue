<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { swap } from 'src/stores/export'
import { computed, onMounted, watch } from 'vue'
import { throttle } from 'lodash-es'

const blockHash = computed(() => swap.Swap.blockHash())

const getPools = throttle(() => {
  swap.Swap.getPools()
}, 10000, {
  leading: false, 
  trailing: true
})

watch(blockHash, () => {
  getPools()
})

onMounted(() => {
  swap.Swap.getPools()
  swap.Swap.initialize()
})

</script>
