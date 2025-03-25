<template>
  <div>
    <q-input v-model='argument.meme.name' :label='$t("MSG_NAME")' hide-bottom-space :error='nameError' />
    <q-input v-model='argument.meme.ticker' :label='$t("MSG_TICKER")' hide-bottom-space :error='tickerError' />
    <div
      :class='[ "file-upload-area vertical-inner-y-margin", imageError ? "file-upload-area-error shake" : "" ]'
      @dragover.prevent
      @drop.prevent='onFileDrop'
      @click='onInputImage'
    >
      <div v-if='imageUrl' class='image-preview'>
        <q-img :src='imageUrl' fit='scale-down' width='360px' height='100%' />
      </div>
      <q-item-label v-else class='text-h6 text-grey-6'>
        <q-icon name='bi-image' size='32px' />
        <div>{{ $t('MSG_CLICK_OR_DRAG_IMAGE') }}</div>
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
    <q-input v-model='argument.meme.metadata.description' type='textarea' filled :label='$t("MSG_DESCRIPTION")' />
    <q-expansion-item
      dense
      expand-icon-toggle
      :label='$t("MSG_MORE_OPTIONS")'
      v-model='expanded'
      class='vertical-inner-y-margin text-grey-8 text-left text-bold'
    >
      <div>
        <q-input dense v-model='argument.meme.metadata.website' :label='$t("MSG_OFFICIAL_WEBSITE") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.twitter' :label='$t("MSG_TWITTER") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.telegram' :label='$t("MSG_TELEGRAM") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.discord' :label='$t("MSG_DISCORD") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.github' :label='$t("MSG_GITHUB") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input
          dense
          v-model='argument.meme.initialSupply' type='number' :label='$t("MSG_INITIAL_SUPPLY")' :rules='[val => !!val || "Field is required"]'
          hide-bottom-space
        />
        <q-input
          dense
          v-model='argument.meme.decimals' type='number' :label='$t("MSG_DECIMALS")' :rules='[val => !!val || "Field is required"]'
          hide-bottom-space
        />
        <q-toggle dense v-model='hasInitialLiquidity' class='vertical-inner-y-margin' :label='$t("MSG_INITIAL_LIQUIDITY")' />
        <div class='vertical-inner-y-margin' />
        <div v-if='hasInitialLiquidity'>
          <q-input
            dense
            v-model='initialLiquidity.fungibleAmount' type='number' :label='$t("MSG_TOKEN_AMOUNT")' :rules='[val => !!val || "Field is required"]'
            hide-bottom-space
          />
          <q-input
            dense
            v-model='initialLiquidity.nativeAmount' type='number' :label='$t("MSG_NATIVE_AMOUNT")' :rules='[val => !!val || "Field is required"]'
            hide-bottom-space
          />
          <q-toggle dense v-model='parameters.virtualInitialLiquidity' class='vertical-inner-y-margin' :label='$t("MSG_VIRTUAL_INITIAL_LIQUIDITY")' />
          <div class='vertical-inner-y-margin' />
        </div>
      </div>
    </q-expansion-item>
    <q-btn
      rounded flat class='border-red-4 full-width vertical-section-y-margin' :label='$t("MSG_CREATE_MEME")'
      @click='onCreateMemeClick'
    />
  </div>
</template>

<script lang='ts' setup>
import { QInput } from 'quasar'
import { CREATE_MEME, PUBLISH_DATA_BLOB } from 'src/graphql'
import { meme, user, store } from 'src/localstore'
import { computed, ref } from 'vue'
import * as lineraWasm from '../../../dist/wasm/linera_wasm'
import { stringify } from 'lossless-json'
import { constants } from 'src/constant'

const argument = ref({
  meme: {
    initialSupply: '21000000',
    decimals: 6,
    metadata: {
      description: "Creator didn't leave any information about this token. You should know if you interact with malfunction application, you may lose your assets!"
    }
  }
} as meme.InstantiationArgument)
const hasInitialLiquidity = ref(false)
const initialLiquidity = ref({
  fungibleAmount: '0',
  nativeAmount: '0'
} as meme.Liquidity)
const parameters = ref({} as meme.MemeParameters)

const nameError = ref(false)
const tickerError = ref(false)
const imageError = ref(false)

const expanded = ref(false)

const _user = user.useUserStore()
const publicKey = computed(() => _user.publicKey)
const chainId = computed(() => _user.chainId)

const MAXSIZE = 4 * 1024 * 1024
const errorMessage = ref('')
const logoBytes = ref(new Uint8Array())
const imageUrl = ref('')

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
          logoBytes.value = new Uint8Array(arrayBuffer)
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
          logoBytes.value = new Uint8Array(arrayBuffer)
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

const publishDataBlob = (): Promise<string> => {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
  return new Promise((resolve, reject) => {
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        publicKey: publicKey.value,
        query: {
          query: PUBLISH_DATA_BLOB.loc?.source?.body,
          variables: {
            chainId: chainId.value,
            blobHash: argument.value.meme.metadata.logo
          }
        },
        operationName: 'publishDataBlob'
      }
    }).then((blobHash) => {
      resolve(blobHash as string)
    }).catch((e) => {
      reject(e)
    })
  })
}

const createMeme = async (): Promise<string> => {
  const variables = {
    memeInstantiationArgument: argument.value,
    memeParameters: parameters.value
  }
  const queryBytes = await lineraWasm.graphql_deserialize_proxy_operation(CREATE_MEME.loc?.source?.body as string, stringify(variables) as string)
  return new Promise((resolve, reject) => {
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: constants.applicationId(constants.APPLICATION_URLS.PROXY),
        publicKey: publicKey.value,
        query: {
          query: PUBLISH_DATA_BLOB.loc?.source?.body,
          variables: {
            chainId: chainId.value,
            blobHash: argument.value.meme.metadata.logo
          },
          bytes: queryBytes,
          blobs: [logoBytes.value]
        },
        operationName: 'createMeme'
      }
    }).then((blobHash) => {
      resolve(blobHash as string)
    }).catch((e) => {
      reject(e)
    })
  })
}

const onCreateMemeClick = async () => {
  try {
    const blobHash = await lineraWasm.blob_hash(`[${logoBytes.value.toString()}]`)
    argument.value.meme.metadata.logo = blobHash
    argument.value.meme.metadata.logoStoreType = store.StoreType.Blob
    await publishDataBlob()
    await createMeme()
  } catch (e) {
    console.log(e)
  }
}

</script>

<style lang='sass' scoped>
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
  background: #ebebeb

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
