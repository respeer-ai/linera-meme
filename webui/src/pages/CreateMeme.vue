<template>
  <CreateMeme class='main-content' />
</template>

<script setup lang='ts'>
import { defineAsyncComponent } from 'vue'

const CreateMeme = defineAsyncComponent(() => import('src/components/meme/CreateMeme.vue'))

</script>
