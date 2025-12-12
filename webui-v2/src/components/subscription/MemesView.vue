<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { proxy } from 'src/stores/export'
import { computed, onMounted, watch } from 'vue'
import { throttle } from 'lodash-es'

const blockHash = computed(() => proxy.Proxy.blockHash())

const getMemeApplications = throttle(() => {
  proxy.Proxy.getMemeApplications()
}, 10000, {
  leading: false, 
  trailing: true
})

watch(blockHash, () => {
  getMemeApplications()
})

onMounted(() => {
  proxy.Proxy.getMemeApplications()
  proxy.Proxy.initialize()
})

</script>
