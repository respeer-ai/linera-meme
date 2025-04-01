<template>
  <q-page class='flex items-center justify-center'>
    <div class='text-center'>
      <div class='text-bold text-grey-9' :style='{fontSize: "28px"}'>
        Let's Pump
      </div>
      <CreateMemeInner @created='onMemeTokenCreated' @creating='onMemeTokenCreating' @error='onCreateMemeTokenError' />
    </div>
  </q-page>
  <q-dialog v-model='showing' :persistent='creating' @hide='onConfirmed'>
    <q-card class='dialog flex items-center justify-center'>
      <q-inner-loading
        :showing='creating'
        :label='loadingLabel'
        label-style='font-size: 1.1em'
      />
      <div v-if='createMessage.length && !creating' class='error'>
        <div class='row' :style='{lineHeight: "48px"}'>
          <q-space />
          <q-icon :name='createError ? "bi-exclamation-circle" : "bi-check-circle"' :color='createError ? "orange-6" : "green-6"' size='48px' class='horizontal-inner-x-margin-right' />
          <div class='text-bold text-grey-9' :style='{fontSize: "20px"}'>
            {{ createError ? $t('MSG_CREATE_ERROR') : $t('MSG_CREATE_SUCCESSFUL') }}
          </div>
          <q-space />
        </div>
        <div class='word-break-all vertical-section-y-margin'>
          {{ createMessage }}
        </div>
        <q-btn
          rounded flat class='border-red-4 full-width vertical-section-y-margin' :label='$t("MSG_CONTINUE")'
          @click='onContinueClick'
        />
      </div>
    </q-card>
  </q-dialog>
</template>
<script setup lang='ts'>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

import CreateMemeInner from './CreateMemeInner.vue'

const { t } = useI18n({ useScope: 'global' })

const showing = ref(false)
const creating = ref(false)
const createError = ref(false)
const loadingLabel = ref(t('MSG_CREATING'))
const createMessage = ref('')

const router = useRouter()

const onConfirmed = () => {
  showing.value = false
}

const onContinueClick = () => {
  showing.value = false
  setTimeout(() => {
    void router.push({ path: '/meme' })
  }, 1000)
}

const onMemeTokenCreated = () => {
  creating.value = false
  createMessage.value = t('MSG_APPLICATION_CREATED')
}

const onMemeTokenCreating = () => {
  showing.value = true
  creating.value = true
  createMessage.value = t('MSG_CREATING')
}

const onCreateMemeTokenError = (error: string) => {
  creating.value = false
  createError.value = true
  createMessage.value = JSON.stringify(error)
}

</script>

<style lang='sass' scoped>
.long-text
  width: 500px
  border: 1px solid #ccc
  overflow-wrap: break-word
  word-break: break-word

.dialog
  width: 600px
  min-height: 240px
  padding: 24px

.error
  font-size: 16px
</style>
