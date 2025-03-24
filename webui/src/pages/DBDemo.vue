<template>
  <OneMM />
</template>

<script setup lang='ts'>
import { defineAsyncComponent } from 'vue'

const OneMM = defineAsyncComponent(() => import('src/components/bridge/db/OneMM.vue'))
</script>
