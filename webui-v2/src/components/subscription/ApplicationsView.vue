<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { ams } from 'src/stores/export'
import { computed, onMounted, watch } from 'vue'
import { throttle } from 'lodash-es'

const blockHash = computed(() => ams.Ams.blockHash())

const getApplications = throttle(() => {
  ams.Ams.getApplications()
}, 10000, {
  leading: false, 
  trailing: true
})

watch(blockHash, () => {
  getApplications()
})

onMounted(() => {
  ams.Ams.getApplications()
})

</script>
