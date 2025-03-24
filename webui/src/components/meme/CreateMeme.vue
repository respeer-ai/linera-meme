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
import { ApolloClient } from '@apollo/client/core'
import gql from 'graphql-tag'
import { getAppClientOptions } from 'src/apollo'
import { provideApolloClient, useMutation } from '@vue/apollo-composable'
import { useUserStore } from 'src/mystore/user'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { InitPoolLiquidity } from 'src/stores/memeInfo'

import CreateMemeInner from './CreateMemeInner.vue'
import ChainMemeBridge from '../bridge/db/ChainMemeBridge.vue'
import { useHostStore } from 'src/mystore/host'

const { t } = useI18n({ useScope: 'global' })

const user = useUserStore()
const account = computed(() => user.account?.trim())
const chainId = computed(() => user.chainId?.trim())

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

const swapCreationChainID = ref(useHostStore().swapCreationChainId)
const swapAppID = ref(useHostStore().swapApplicationId)
const wlineraAppID = ref(useHostStore().wlineraApplicationId)
const swapEndPoint = ref(useHostStore()._swapEndpoint())

// approve
const newAppApprove = ref('4500000')
// mint
const wlineraMint = ref('10')
// approve
const wlineraApprove = ref('5')
// create pool
const initPoolLiquidity = ref({
  amount0Initial: '5',
  amount1Initial: '1',
  amount0Virtual: '5',
  amount1Virtual: '1'
} as InitPoolLiquidity)

const applicationCreatorChainId = (id: string) => {
  const firstPartLength = 128
  const middlePartLength = 64
  const lastPartLength = 24
  const totalLength = firstPartLength + middlePartLength + lastPartLength
  if (id.length !== totalLength) {
    throw new Error('Invalid ID length')
  }

  const middlePart = id.slice(firstPartLength, firstPartLength + middlePartLength)
  return middlePart
}

const requestApplication = async (appID: string) => {
  const publicKey = account.value
  const creatorChainId = applicationCreatorChainId(appID)
  const query = gql`
    mutation requestApplication ($chainId: String!, $applicationId: String!, $targetChainId: String!) {
      requestApplication(chainId: $chainId, applicationId: $applicationId, targetChainId: $targetChainId)
    }`
  return new Promise((resolve, reject) => {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        publicKey: publicKey,
        query: {
          query: query.loc?.source?.body,
          variables: {
            chainId: chainId.value,
            applicationId: appID,
            targetChainId: creatorChainId
          },
          operationName: 'requestApplication'
        }
      }
    }).then((result) => {
      resolve(result)
    }).catch((e) => {
      reject(e)
    })
  })
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const createPool = async (appID: string, token0: string, token1: string, amount0Initial: string, amount1Initial: string, amount0Virtual: string, amount1Virtual: string): Promise<any> => {
  const publicKey = account.value
  const query = gql`
    mutation createPool ($token0: String!, $token1: String!, $amount0Initial: String!, $amount1Initial: String!, $amount0Virtual: String!, $amount1Virtual: String!) {
      createPool(token0: $token0, token1: $token1, amount0Initial: $amount0Initial, amount1Initial: $amount1Initial, amount0Virtual: $amount0Virtual, amount1Virtual: $amount1Virtual)
    }`
  return new Promise((resolve, reject) => {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: appID,
        publicKey: publicKey,
        query: {
          query: query.loc?.source?.body,
          variables: {
            token0: token0,
            token1: token1,
            amount0Initial: amount0Initial,
            amount1Initial: amount1Initial,
            amount0Virtual: amount0Virtual,
            amount1Virtual: amount1Virtual
          },
          operationName: 'createPool'
        }
      }
    }).then((result) => {
      resolve(result)
    }).catch((e) => {
      reject(e)
    })
  })
}

const onCreateLiquidityPool = async () => {
  step.value += 1
  loadingLabel.value = t('MSG_CREATING_LIQUIDITY_POOL')

  const appID = swapAppID.value
  const token0 = applicationId.value
  const token1 = wlineraAppID.value

  await createPool(appID, token0, token1, initPoolLiquidity.value.amount0Initial, initPoolLiquidity.value.amount1Initial, initPoolLiquidity.value.amount0Virtual, initPoolLiquidity.value.amount1Virtual)
    .then(() => {
      creating.value = false
      createMessage.value = applicationId.value
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed create liquidity pool: ${JSON.stringify(e)}`
    })
}

const onAuthorizeWlineraToSwap = () => {
  step.value += 1
  loadingLabel.value = t('MSG_AUTHORIZING_WLINERA_TO_SWAP')

  if (initPoolLiquidity.value.amount0Initial === '0' && initPoolLiquidity.value.amount1Initial === '0') {
    setTimeout(() => void onCreateLiquidityPool(), 100)
    return
  }

  const appID = wlineraAppID.value
  if (Number(wlineraApprove.value) < Number(initPoolLiquidity.value.amount1Initial)) {
    wlineraApprove.value = initPoolLiquidity.value.amount1Initial
  }
  const chainId = swapCreationChainID.value
  const owner = 'Application:' + swapAppID.value
  const amount = wlineraApprove.value

  approve(appID, amount, chainId, owner)
    .then(() => {
      setTimeout(() => void onCreateLiquidityPool(), 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed authorize Wlinera to Swap: ${JSON.stringify(e)}`
    })
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mint = async (appID: string, amount: string): Promise<any> => {
  const publicKey = account.value

  const query = gql`
    mutation mint ($amount: String!) {
      mint(amount: $amount)
    }`
  return new Promise((resolve, reject) => {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: appID,
        publicKey: publicKey,
        query: {
          query: query.loc?.source?.body,
          variables: {
            amount
          },
          operationName: 'mint'
        }
      }
    }).then((result) => {
      resolve(result)
    }).catch((e) => {
      reject(e)
    })
  })
}

const onMintWlinera = () => {
  step.value += 1
  loadingLabel.value = t('MSG_MINTING_WLINERA')

  if (initPoolLiquidity.value.amount0Initial === '0' && initPoolLiquidity.value.amount1Initial === '0') {
    setTimeout(() => void onAuthorizeWlineraToSwap(), 100)
    return
  }

  const appID = wlineraAppID.value
  if (Number(wlineraMint.value) < Number(initPoolLiquidity.value.amount1Initial)) {
    wlineraMint.value = initPoolLiquidity.value.amount1Initial
  }
  const amount = wlineraMint.value

  mint(appID, amount)
    .then(() => {
      setTimeout(() => void onAuthorizeWlineraToSwap(), 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed mint Wlinera for initial liquidity: ${JSON.stringify(e)}`
    })
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const approve = async (appID: string, amount: string, chainId: string, owner: string): Promise<any> => {
  const publicKey = account.value
  const query = gql`
    mutation approve($chainId: String!, $owner: String!, $amount: String!) {
      approve(spender: {chain_id: $chainId, owner: $owner}, value: $amount)
    }`
  return new Promise((resolve, reject) => {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: appID,
        publicKey: publicKey,
        query: {
          query: query.loc?.source?.body,
          variables: {
            chainId,
            owner,
            amount
          },
          operationName: 'approve'
        }
      }
    }).then((result) => {
      resolve(result)
    }).catch((e) => {
      reject(e)
    })
  })
}

const onAuthorizeInitialBalanceToSwap = () => {
  step.value += 1
  loadingLabel.value = t('MSG_AUTHORIZING_INITIAL_BALANCE_TO_SWAP')

  const appID = applicationId.value
  const amount = newAppApprove.value
  const chainId = swapCreationChainID.value
  const owner = 'Application:' + swapAppID.value

  approve(appID, amount, chainId, owner)
    .then(() => {
      setTimeout(() => void onMintWlinera(), 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed authorize initial balance to Swap: ${JSON.stringify(e)}`
    })
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const subscribeCreatorChain = (appID: string): Promise<any> => {
  const publicKey = account.value
  const query = gql`
    mutation subscribeCreatorChain {
      subscribeCreatorChain
    }`
  return new Promise((resolve, reject) => {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: appID,
        publicKey: publicKey,
        query: {
          query: query.loc?.source?.body,
          variables: {},
          operationName: 'subscribeCreatorChain'
        }
      }
    }).then((result) => {
      resolve(result)
    }).catch((e) => {
      reject(e)
    })
  })
}

const onSubscribeSwapCreatorChain = () => {
  step.value += 1
  loadingLabel.value = t('MSG_SUBSCRIBING_SWAP_CREATOR_CHAIN')

  subscribeCreatorChain(swapAppID.value)
    .then(() => {
      setTimeout(() => void onAuthorizeInitialBalanceToSwap(), 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed subscribe Swap creator chain: ${JSON.stringify(e)}`
    })
}

const onSubscribeWlineraCreatorChain = () => {
  step.value += 1
  loadingLabel.value = t('MSG_SUBSCRIBING_WLINERA_CREATOR_CHAIN')

  subscribeCreatorChain(wlineraAppID.value)
    .then(() => {
      setTimeout(onSubscribeSwapCreatorChain, 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed subscribe Wlinera creator chain: ${JSON.stringify(e)}`
    })
}

const requestApplicationWithUrl = async (url: string, chainId: string, applicationId: string, targetChainId: string) => {
  const appOptions = /* await */ getAppClientOptions(url)
  const appApolloClient = new ApolloClient(appOptions)

  const { mutate } = provideApolloClient(appApolloClient)(() => useMutation(gql`
    mutation requestApplication ($chainId: String!, $applicationId: String!, $targetChainId: String!) {
      requestApplication(chainId: $chainId, applicationId: $applicationId, targetChainId: $targetChainId)
    }
  `))

  return new Promise((resolve, reject) => {
    mutate({
      chainId: chainId,
      applicationId: applicationId,
      targetChainId: targetChainId
    }).then((result) => {
      resolve(result)
    }).catch((e) => {
      reject(e)
    })
  })
}

const onRequestCreatedApplicationToSwapChain = () => {
  step.value += 1
  loadingLabel.value = t('MSG_REQUESTING_CREATED_APPLICATION_TO_SWAP_CHAIN')

  const url = swapEndPoint.value
  const swapChainId = swapCreationChainID.value
  const targetChainId = chainId.value

  requestApplicationWithUrl(url, swapChainId, applicationId.value, targetChainId)
    .then(() => {
      setTimeout(onSubscribeWlineraCreatorChain, 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed request application to swap chain: ${JSON.stringify(e)}`
    })
}

const onRequestSwap = () => {
  step.value += 1
  loadingLabel.value = t('MSG_REQUESTING_SWAP')

  requestApplication(swapAppID.value)
    .then(() => {
      setTimeout(onRequestCreatedApplicationToSwapChain, 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed request swap: ${JSON.stringify(e)}`
    })
}

const onRequestWlinera = () => {
  step.value += 1
  loadingLabel.value = t('MSG_REQUESTING_WLINERA')

  requestApplication(wlineraAppID.value)
    .then(() => {
      setTimeout(onRequestSwap, 100)
    })
    .catch((e) => {
      creating.value = false
      createError.value = true
      createMessage.value = `Failed request wlinera: ${JSON.stringify(e)}`
    })
}

const chainMemeBridge = ref<InstanceType<typeof ChainMemeBridge>>()

const onMemeTokenCreated = async (_applicationId: string) => {
  applicationId.value = _applicationId
  // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-call
  await chainMemeBridge.value?.add(chainId.value, _applicationId)
  onRequestWlinera()
}

const onPoolInitLiquidity = (liquidity: InitPoolLiquidity) => {
  initPoolLiquidity.value = liquidity
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
