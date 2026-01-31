<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { blob } from 'src/stores/export'
import { computed, onMounted, watch } from 'vue'
import { throttle } from 'lodash-es'

const blockHash = computed(() => blob.Blob.blockHash())

const getBlobsList = throttle(() => {
  blob.Blob.getBlobsList()
}, 10000, {
  leading: false, 
  trailing: true
})

watch(blockHash, () => {
  getBlobsList()
})

onMounted(() => {
  blob.Blob.getBlobsList()
  blob.Blob.initialize()
})

</script>
