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
      <create-meme-view @created='onMemeCreated' @error='onCreateMemeError' />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { notify } from 'src/stores/export'

import CreateMemeView from './CreateMemeView.vue'

const creating = ref(false)

const onCreateMemeClick = () => {
  creating.value = true
}

const onMemeCreated = () => {
  creating.value = false
}

const onCreateMemeError = (e: string) => {
  notify.Notify.pushNotification({
    Title: 'Create meme token',
    Message: `Failed create meme token: ${e}`,
    Popup: true,
    Type: notify.NotifyType.Error
  })
}

</script>

<style scoped lang='sass'>
::v-deep(.q-btn)
  .q-icon.material-icons
    color: white
</style>
