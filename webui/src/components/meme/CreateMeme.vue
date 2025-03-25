<template>
  <q-page class='flex items-center justify-center'>
    <q-stepper
      v-model='step'
      header-nav
      ref='stepper'
      color='primary'
      class='content-narrow'
      animated
      vertical
      flat
    >
      <q-step
        :name='1'
        :title='$t("MSG_CREATE_MEME_APPLICATION")'
        icon='settings'
        :done='step > 1'
        :header-nav='step > 1'
      >
        <CreateMemeInner @created='onMemeTokenCreated' @init-pool-liquidity='onPoolInitLiquidity' @creating='onMemeTokenCreating' @error='onCreateMemeTokenError' />
      </q-step>

      <q-step
        :name='2'
        :title='$t("MSG_REQUEST_WLINERA")'
        icon='create_new_folder'
        :done='step > 2'
        :header-nav='step > 2'
      />

      <q-step
        :name='3'
        :title='$t("MSG_REQUEST_SWAP")'
        icon='create_new_folder'
        :done='step > 3'
        :header-nav='step > 3'
      />

      <q-step
        :name='4'
        :title='$t("MSG_REQUEST_APPLICATION_TO_SWAP_CHAIN")'
        icon='create_new_folder'
        :done='step > 4'
        :header-nav='step > 4'
      />

      <q-step
        :name='5'
        :title='$t("MSG_SUBSCRIBE_WLINERA_CREATOR_CHAIN")'
        icon='create_new_folder'
        :done='step > 5'
        :header-nav='step > 5'
      />

      <q-step
        :name='6'
        :title='$t("MSG_SUBSCRIBE_SWAP_CREATOR_CHAIN")'
        icon='create_new_folder'
        :done='step > 6'
        :header-nav='step > 6'
      />

      <q-step
        :name='7'
        :title='$t("MSG_AUTHORIZE_INITIAL_BALANCE_TO_SWAP")'
        :done='step > 7'
        :header-nav='step > 7'
      />

      <q-step
        :name='8'
        :title='$t("MSG_MINT_WLINERA")'
        icon='create_new_folder'
        :done='step > 8'
        :header-nav='step > 8'
      />

      <q-step
        :name='9'
        :title='$t("MSG_AUTHORIZE_INITIAL_WLINERA_TO_SWAP")'
        icon='create_new_folder'
        :done='step > 9'
        :header-nav='step > 9'
      />

      <q-step
        :name='10'
        :title='$t("MSG_CREATE_LIQUIDITY_POOL")'
        icon='create_new_folder'
        :done='step > 10'
        :header-nav='step > 10'
      />
    </q-stepper>
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
  <ChainMemeBridge ref='chainMemeBridge' />
</template>
<script setup lang='ts'>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { user } from 'src/localstore'

import CreateMemeInner from './CreateMemeInner.vue'
import ChainMemeBridge from '../bridge/db/ChainMemeBridge.vue'

const { t } = useI18n({ useScope: 'global' })

const _user = user.useUserStore()
const chainId = computed(() => _user.chainId?.trim())

const showing = ref(false)
const creating = ref(false)
const createError = ref(false)
const loadingLabel = ref(t('MSG_CREATING'))
const createMessage = ref('')
const applicationId = ref('')

const router = useRouter()

const onConfirmed = () => {
  showing.value = false
}

const onContinueClick = () => {
  showing.value = false
  void router.push({ path: '/meme' })
}

const step = ref(1)

const onPoolInitLiquidity = () => {
  // TODO
}

const chainMemeBridge = ref<InstanceType<typeof ChainMemeBridge>>()

const onMemeTokenCreated = async (_applicationId: string) => {
  applicationId.value = _applicationId
  // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
  await chainMemeBridge.value?.add(chainId.value, _applicationId)
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
