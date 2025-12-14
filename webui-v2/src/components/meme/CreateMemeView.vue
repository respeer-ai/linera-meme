<template>
  <div class='full-height flex flex-col'>
    <div class='full-width'>
      <section-title-view icon='psychology' title="Let's Pump" />
      <div class='q-mt-lg text-neutral font-size-18'>
        <q-icon name='badge' class='text-secondary q-mr-xs' size='24px' />
        Name
      </div>
      <q-input filled v-model='argument.meme.name' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='A great meme name' :autofocus='true' :error='nameError' />
      <div class='q-mt-lg text-neutral font-size-18'>
        <q-icon name='paid' class='text-secondary q-mr-xs' size='24px' />
        Ticker
      </div>
      <q-input filled v-model='argument.meme.ticker' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='A great meme ticker' :autofocus='true' :error='tickerError' />
      <div class='q-mt-lg text-neutral font-size-18'>
        <q-icon name='image' class='text-secondary q-mr-xs' size='24px' />
        Logo
      </div>
      <div
        :class='[ "file-upload-area q-mt-md radius-8", imageError ? "file-upload-area-error" : "" ]'
        @dragover.prevent
        @drop.prevent='onFileDrop'
        @click='onInputImage'
      >
        <div v-if='imageUrl' class='image-preview'>
          <q-img :src='imageUrl' fit='scale-down' width='360px' height='100%' />
        </div>
        <q-item-label v-else class='text-h6 text-grey-6'>
          <q-icon name='image' size='64px' />
          <div>Click or drag to upload an image.</div>
        </q-item-label>
        <input
          ref='fileInput'
          type='file'
          accept='image/*'
          @change='onFileChange'
          style='display: none;'
        >
        <div v-if='imageError' class='error-message'>
          {{ errorMessage }}
        </div>
      </div>
      <div class='q-mt-lg text-neutral font-size-18'>
        <q-icon name='description' class='text-secondary q-mr-xs' size='24px' />
        Description
      </div>
      <div class='q-mt-md'>
        <q-input v-model='argument.meme.metadata.description' type='textarea' filled />
      </div>
      <q-expansion-item
        dense
        expand-icon-toggle
        v-model='expanded'
        class='q-mt-md q-mb-lg font-size-20'
        expand-icon='keyboard_double_arrow_down'
        icon='menu'
        label='Expand'
      >
        <q-toggle dense v-model='hasInitialLiquidity' class='q-mt-md font-size-16' label='Initial Liquidity' />
        <div v-if='hasInitialLiquidity'>
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-icon name='attach_money' class='text-secondary q-mr-xs' size='24px' />
            Initial Liquidity amount
          </div>
          <q-input filled v-model='initialLiquidity.fungibleAmount' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Initial liquidity amount' :autofocus='true' :error='fungibleAmountError' />
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-img :src='constants.LINERA_LOGO' width='24px' height='24px' />
            Native token amount
          </div>
          <q-input filled v-model='initialLiquidity.nativeAmount' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Initial liquidity amount' :autofocus='true' :error='nativeAmountError' />
          <q-toggle dense v-model='parameters.virtualInitialLiquidity' class='q-mt-md' label='Virtual Initial Liquidity' />
        </div>
        <div class='q-mt-lg text-neutral font-size-18'>
          <q-icon name='power_input' class='text-secondary q-mr-xs' size='24px' />
          Initial Supply
        </div>
        <q-input filled v-model='argument.meme.initialSupply' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Initial supply amount' :autofocus='true' />
        <div class='q-mt-lg text-neutral font-size-18'>
          <q-icon name='data_array' class='text-secondary q-mr-xs' size='24px' />
          Decimals
        </div>
        <q-input filled v-model='argument.meme.decimals' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Amount decimals' :autofocus='true' />
        <div>
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-icon name='link' class='text-secondary q-mr-xs' size='24px' />
            Official Website
          </div>
          <q-input filled v-model='argument.meme.metadata.website' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Official website url' :autofocus='true' />
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-avatar size='24px' class='bg-grey-5'>
              <q-img :src='constants.X_LOGO' width='24px' height='24px' />
            </q-avatar>
            X
          </div>
          <q-input filled v-model='argument.meme.metadata.website' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='X handle' :autofocus='true' />
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-avatar size='24px' class='bg-grey-5'>
              <q-img :src='constants.TELEGRAM_LOGO' width='24px' height='24px' />
            </q-avatar>
            Telegram
          </div>
          <q-input filled v-model='argument.meme.metadata.website' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Telegram link' :autofocus='true' />
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-avatar size='24px' class='bg-grey-5'>
              <q-img :src='constants.DISCORD_LOGO' width='24px' height='24px' />
            </q-avatar>
            Discord
          </div>
          <q-input filled v-model='argument.meme.metadata.website' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Discord link' :autofocus='true' />
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-avatar size='24px' class='bg-grey-5'>
              <q-img :src='constants.GITHUB_LOGO' width='24px' height='24px' />
            </q-avatar>
            Github
          </div>
          <q-input filled v-model='argument.meme.metadata.website' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Github link' :autofocus='true' />
          <div class='q-mt-lg text-neutral font-size-18'>
            <q-icon name='live_tv' class='text-secondary q-mr-xs' size='24px' />
            Live Stream
          </div>
          <q-input filled v-model='argument.meme.metadata.website' class='font-size-16 text-neutral text-bold full-width q-mt-sm' placeholder='Live stream url (youtube)' :autofocus='true' />
        </div>
      </q-expansion-item>
    </div>
    <q-btn rounded class='bg-primary flex justify-center items-center hover-primary full-width q-mt-auto' @click='onCreateMemeClick'>
      <div class='row flex justify-center items-center'>
        <q-icon name='add' />
        <span class='q-header-line'>Create Meme</span>
      </div>
    </q-btn>
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { meme, blob, ams, store, user } from 'src/stores/export'
import { constants } from 'src/constant'
import { Wallet } from 'src/wallet'
import { creatorChainId } from 'src/utils'

import SectionTitleView from '../common/SectionTitleView.vue'

const imageError = ref(false)
const nameError = ref(false)
const tickerError = ref(false)

const fungibleAmountError = ref(false)
const nativeAmountError = ref(false)

const MAXSIZE = 4 * 1024 * 1024
const errorMessage = ref('')
const logoBytes = ref([] as number[])
const imageUrl = ref('')

const expanded = ref(false)

const onFileDrop = (event: DragEvent): void => {
  const files = event.dataTransfer?.files
  const file = files?.[0]
  if (file) {
    if (file.size > MAXSIZE) {
      imageError.value = true
      errorMessage.value = 'The image size must not exceed 4MB.'
      throw new Error(errorMessage.value)
    }
    errorMessage.value = ''
    imageError.value = false
    const reader = new FileReader()
    reader.onload = (e: ProgressEvent<FileReader>): void => {
      if (e.target) {
        const arrayBuffer = e.target.result as ArrayBuffer
        const blob = new Blob([arrayBuffer], { type: file.type })
        const url = URL.createObjectURL(blob)
        imageUrl.value = url

        if (arrayBuffer instanceof ArrayBuffer) {
          logoBytes.value = Array.from(new Uint8Array(arrayBuffer))
        }
      }
    }
    reader.readAsArrayBuffer(file)
  }
}

const onFileChange = (event: Event): void => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    if (file.size > MAXSIZE) {
      imageError.value = true
      errorMessage.value = 'The image size must not exceed 4MB.'
      throw new Error(errorMessage.value)
    }
    errorMessage.value = ''
    imageError.value = false
    const reader = new FileReader()
    reader.onload = (e: ProgressEvent<FileReader>): void => {
      if (e.target) {
        const arrayBuffer = e.target.result as ArrayBuffer
        const blob = new Blob([arrayBuffer], { type: file.type })
        const url = URL.createObjectURL(blob)
        imageUrl.value = url

        if (arrayBuffer instanceof ArrayBuffer) {
          logoBytes.value = Array.from(new Uint8Array(arrayBuffer))
        }
      }
    }
    reader.readAsArrayBuffer(file)
  }
}

const fileInput = ref<HTMLInputElement>()

const onInputImage = () => {
  fileInput.value?.click()
}

const argument = ref({
  meme: {
    initialSupply: '21000000',
    totalSupply: '21000000',
    decimals: 6,
    metadata: {
      description: "Creator didn't leave any information about this token. You should know if you interact with malfunction application, you may lose your assets!"
    },
    virtualInitialLiquidity: true
  }
} as meme.InstantiationArgument)
// TODO: We put all in liquidity in this version. It should be removed in future
const hasInitialLiquidity = ref(true)
const initialLiquidity = ref({
  fungibleAmount: (Number(argument.value.meme.initialSupply) - 100).toString(),
  nativeAmount: '8720'
} as meme.Liquidity)
const parameters = ref({
  virtualInitialLiquidity: true
} as meme.MemeParameters)

const createMeme = async (): Promise<string> => {
  if (hasInitialLiquidity.value) {
    fungibleAmountError.value = Number(initialLiquidity.value.fungibleAmount) <= 0
    nativeAmountError.value = Number(initialLiquidity.value.nativeAmount) <= 0
    if (fungibleAmountError.value || nativeAmountError.value) {
      return 'error'
    }
  }

  parameters.value.creator = await user.User.account()
  parameters.value.swapCreatorChainId = await creatorChainId.creatorChainId('swap')

  if (hasInitialLiquidity.value) {
    parameters.value.initialLiquidity = initialLiquidity.value
  }

  argument.value.amsApplicationId = constants.applicationId(constants.APPLICATION_URLS.AMS) as string
  argument.value.blobGatewayApplicationId = constants.applicationId(constants.APPLICATION_URLS.BLOB_GATEWAY) as string

  const variables = {
    memeInstantiationArgument: argument.value,
    memeParameters: parameters.value
  }

  return await Wallet.createMeme(argument.value, parameters.value, variables)
}

const emit = defineEmits<{
  (ev: 'created'): void,
  (ev: 'creating'): void,
  (ev: 'error', error: string): void
}>()

const onCreateMemeClick = async () => {
  try {
    if (logoBytes.value.length === 0) imageError.value = true
    if (!argument.value.meme.name?.length) nameError.value = true
    if (!argument.value.meme.ticker?.length) tickerError.value = true

    if (imageError.value || nameError.value || tickerError.value) {
      return
    }

    const blobHash = await Wallet.blobHash(logoBytes.value) as string

    imageError.value = blob.Blob.existBlob(blobHash)
    nameError.value = ams.Ams.existMeme(argument.value.meme.name, argument.value.meme.ticker)

    if (imageError.value || nameError.value || tickerError.value) {
      return
    }

    argument.value.meme.metadata.logo = blobHash
    argument.value.meme.metadata.logoStoreType = store.StoreType.Blob

    await Wallet.publishDataBlob(logoBytes.value, blobHash)

    setTimeout(() => {
      createMeme().then(() => {
        emit('created')
      }).catch((e: string) => {
        emit('error', e)
      })
    }, 100)
  } catch (e) {
    emit('error', JSON.stringify(e))
  }
}

</script>

<style scoped lang='sass'>
.file-upload-area
  border: 2px dashed #ccc
  padding: 20px
  text-align: center
  cursor: pointer
  margin-bottom: 20px
  display: flex
  flex-direction: column
  justify-content: center
  align-items: center
  height: 180px
  width: 100%

.file-upload-area-error
  border: 2px dashed $red-6

.image-preview
  top: 0
  left: 0
  right: 0
  bottom: 0
  display: flex
  justify-content: center
  align-items: center

.image-preview .q-img
  height: 170px
  max-width: 100%
  max-height: 170px
  object-fit: contain

:deep(.q-item, .q-item--dense)
    padding: 0 !important

.error-message
  color: red
  margin-top: 10px
</style>