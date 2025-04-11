<template>
  <div :style='{paddingBottom: "16px"}'>
    <q-input
      v-model='argument.meme.name'
      :label='$t("MSG_NAME")'
      hide-bottom-space
      :error='nameError'
      @focus='onNameFocus'
    />
    <q-input
      v-model='argument.meme.ticker'
      :label='$t("MSG_TICKER")'
      hide-bottom-space
      :error='tickerError'
      @focus='onTickerFocus'
    />
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
      <q-toggle dense v-model='hasInitialLiquidity' class='vertical-inner-y-margin' :label='$t("MSG_INITIAL_LIQUIDITY")' />
      <div class='vertical-inner-y-margin' />
      <div v-if='hasInitialLiquidity'>
        <q-input
          dense
          v-model='initialLiquidity.fungibleAmount' type='number' :label='$t("MSG_TOKEN_AMOUNT")' :rules='[val => !!val || "Field is required"]'
          hide-bottom-space
          :error='fungibleAmountError'
        />
        <q-input
          dense
          v-model='initialLiquidity.nativeAmount' type='number' :label='$t("MSG_NATIVE_AMOUNT")' :rules='[val => !!val || "Field is required"]'
          hide-bottom-space
          :error='nativeAmountError'
        />
        <q-toggle dense v-model='parameters.virtualInitialLiquidity' class='vertical-inner-y-margin' :label='$t("MSG_VIRTUAL_INITIAL_LIQUIDITY")' />
        <div class='vertical-inner-y-margin' />
      </div>
      <div>
        <q-input dense v-model='argument.meme.metadata.website' :label='$t("MSG_OFFICIAL_WEBSITE") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.twitter' :label='$t("MSG_TWITTER") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.telegram' :label='$t("MSG_TELEGRAM") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.discord' :label='$t("MSG_DISCORD") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.github' :label='$t("MSG_GITHUB") + " (" + $t("MSG_OPTIONAL") + ")"' />
        <q-input dense v-model='argument.meme.metadata.liveStream' :label='$t("MSG_LIVE_STREAM") + " (" + $t("MSG_OPTIONAL") + ")"' />
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
import { meme, user, store, blob, ams, notify } from 'src/localstore'
import { computed, onMounted, ref } from 'vue'
import * as lineraWasm from '../../../dist/wasm/linera_wasm'
import { stringify } from 'lossless-json'
import { constants } from 'src/constant'
import { creatorChainId } from 'src/utils'

const _user = user.useUserStore()
const publicKey = computed(() => _user.publicKey)
const chainId = computed(() => _user.chainId)

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

const fungibleAmountError = ref(false)
const nativeAmountError = ref(false)

const nameError = ref(false)
const tickerError = ref(false)
const imageError = ref(false)

const expanded = ref(false)

const _blob = blob.useBlobStore()
const _ams = ams.useAmsStore()

const MAXSIZE = 4 * 1024 * 1024
const errorMessage = ref('')
const logoBytes = ref([] as number[])
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

const onNameFocus = () => {
  nameError.value = false
}

const onTickerFocus = () => {
  tickerError.value = false
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const publishDataBlob = (): Promise<string> => {
  // Uint8Array will be stringify to map so we should transfer it to array
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
          },
          blobBytes: [JSON.stringify(logoBytes.value)]
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
  if (hasInitialLiquidity.value) {
    fungibleAmountError.value = Number(initialLiquidity.value.fungibleAmount) <= 0
    nativeAmountError.value = Number(initialLiquidity.value.nativeAmount) <= 0
    if (fungibleAmountError.value || nativeAmountError.value) {
      return 'error'
    }
  }

  parameters.value.creator = await user.User.ownerAccount()
  parameters.value.swapCreatorChainId = await creatorChainId.creatorChainId('swap')

  if (hasInitialLiquidity.value) {
    parameters.value.initialLiquidity = initialLiquidity.value
  }

  argument.value.amsApplicationId = constants.applicationId(constants.APPLICATION_URLS.AMS)
  argument.value.blobGatewayApplicationId = constants.applicationId(constants.APPLICATION_URLS.BLOB_GATEWAY)

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
          query: CREATE_MEME.loc?.source?.body,
          variables: {
            memeInstantiationArgument: stringify(argument.value),
            memeParameters: stringify(parameters.value)
          },
          applicationOperationBytes: queryBytes
        },
        operationName: 'createMeme'
      }
    }).then((hash) => {
      resolve(hash as string)
    }).catch((e) => {
      reject(e)
    })
  })
}

// eslint-disable-next-line no-undef
const emit = defineEmits<{(ev: 'created'): void,
  (ev: 'creating'): void,
  (ev: 'error', error: string)
}>()

const onCreateMemeClick = async () => {
  try {
    if (logoBytes.value.length === 0) imageError.value = true
    if (!argument.value.meme.name?.length) nameError.value = true
    if (!argument.value.meme.ticker?.length) tickerError.value = true

    if (imageError.value || nameError.value || tickerError.value) {
      return
    }

    const blobHash = await lineraWasm.blob_hash(`[${logoBytes.value.toString()}]`)

    imageError.value = _blob.existBlob(blobHash)
    nameError.value = _ams.existMeme(argument.value.meme.name)
    tickerError.value = _ams.existMeme(undefined, argument.value.meme.ticker)

    if (imageError.value || nameError.value || tickerError.value) {
      return
    }

    emit('creating')

    argument.value.meme.metadata.logo = blobHash
    argument.value.meme.metadata.logoStoreType = store.StoreType.Blob
    await publishDataBlob()
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

const getApplications = () => {
  _ams.getApplications({
    limit: 40,
    Message: {
      Error: {
        Title: 'Get applications',
        Message: 'Failed get applications',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, (error: boolean, rows?: ams.Application[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

const listBlobs = () => {
  _blob.listBlobs({
    limit: 40,
    Message: {
      Error: {
        Title: 'List blobs',
        Message: 'Failed list blobs',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  })
}

onMounted(() => {
  getApplications()
  listBlobs()
})

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
