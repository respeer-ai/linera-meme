<template>
  <div>
    <q-btn rounded class='bg-primary flex justify-center items-center hover-primary' @click='onCreateMemeClick'>
      <div class='row flex justify-center items-center'>
        <q-icon name='add' />
        <span class='q-header-line'>Create Meme</span>
      </div>
    </q-btn>
  </div>
  <q-dialog dense v-model='creating' position='right' full-height>
    <div style='min-width: 640px;' class='bg-dark-secondary q-pa-lg'>
      <create-meme-view />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { ref } from 'vue'

import CreateMemeView from './CreateMemeView.vue'

const creating = ref(false)

const onCreateMemeClick = () => {
  creating.value = true
}

</script>

<style scoped lang='sass'>
::v-deep(.q-btn)
  .q-icon.material-icons
    color: white
</style>
