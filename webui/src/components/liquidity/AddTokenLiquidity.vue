<template>
  <div class='bg-white popup-padding'>
    <h5>Add Liquidity</h5>
    <q-separator />
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            {{ token0Ticker }}
          </div>
          <div class='text-grey-8' :title='token0Id'>
            {{ shortId(token0Id || '', 5) }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(outBalance).toFixed(2) }}
          </div>
          <div class='text-grey-8'>
            {{ token0Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          class='swap-amount-input text-grey-8' dense v-model.number='tokenZeroAmount' reverse-fill-mask
          input-class='text-right'
          :error='tokenZeroAmountError'
        />
      </div>
    </q-card>
    <div class='row vertical-card-align'>
      <div class='decorate-border-bottom-bold exchange-separator' />
      <div class='exchange-symbol' size='28px'>
        <q-icon name='bi-three-dots' size='14px' class='text-grey-6' />
      </div>
      <div class='decorate-border-bottom-bold exchange-separator' />
    </div>
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-card-align'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            WTLINERA
          </div>
          <div class='text-grey-8' :title='token1'>
            {{ shortId(token1 || '', 5) }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(inBalance).toFixed(2) }}
          </div>
          <div class='text-grey-8'>
            WTLINERA
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          class='swap-amount-input' dense v-model.number='tokenOneAmount' reverse-fill-mask
          input-class='text-right'
          :error='tokenOneAmountError'
        />
      </div>
    </q-card>
    <q-btn
      rounded flat :label='$t("MSG_ADD_LIQUIDITY")' class='full-width border-red-4 vertical-inner-y-margin vertical-inner-y-margin-bottom'
      @click='onAddLiquidity'
    />
  </div>
</template>

<script setup lang='ts'>
import { gql } from '@apollo/client'
import { dbModel } from 'src/model'
import { useNotificationStore } from 'src/mystore/notification'
import { useUserStore } from 'src/mystore/user'
import { useWalletStore } from 'src/mystore/wallet'
import { graphqlResult } from 'src/utils'
import { shortId } from 'src/utils/shortid'
import { ref, watch, onMounted, onUnmounted, toRef } from 'vue'
import { useBlockStore } from 'src/stores/block'
import { useHostStore } from 'src/mystore/host'

interface Props {
  token0Id: string
  token0Ticker: string
}
const props = defineProps<Props>()
const token0Id = toRef(props, 'token0Id')
const token1 = ref(useHostStore().wlineraApplicationId)

const tokenZeroAmount = ref(0)
const tokenOneAmount = ref(0)

const tokenZeroAmountError = ref(false)
const tokenOneAmountError = ref(false)

const outBalance = ref(0)
const inBalance = ref(0)

const walletStore = useWalletStore()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

const subscriptionId = ref(undefined as unknown as string)
const block = useBlockStore()

const validateAmount = (): boolean => {
  tokenZeroAmountError.value = tokenZeroAmount.value > outBalance.value
  tokenOneAmountError.value = tokenOneAmount.value > inBalance.value
  return !(tokenZeroAmountError.value || tokenOneAmountError.value)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const approveToSwap = async (appID: string, publicKey: string, amount: string): Promise<any> => {
  const chainId = useHostStore().swapCreationChainId
  const owner = 'Application:' + useHostStore().swapApplicationId

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

const chainApplications = async (): Promise<string[]> => {
  const applications = gql`
    query applications($chainId: String!) {
      applications(chainId: $chainId) {
        id
      }
    }
  `

  try {
    const res = await window.linera?.request({
      method: 'linera_graphqlQuery',
      params: {
        publicKey: userStore.account,
        query: {
          query: applications.loc?.source?.body,
          variables: {
            chainId: userStore.chainId
          }
        }
      }
    })
    return ((graphqlResult.keyValue(res, 'applications') || []) as Record<string, string>[]).map((el) => el.id)
  } catch (e) {
    console.log('Failed query applications', e)
    return Promise.reject('Failed query applications')
  }
}

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
  const publicKey = userStore.account
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
            chainId: userStore.chainId,
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

const waitChainApplications = async (_applicationIds: string[], timeoutSeconds: number) => {
  const applicationIds = await chainApplications()
  for (const applicationId of _applicationIds) {
    if (!applicationIds.includes(applicationId)) {
      if (timeoutSeconds <= 0) return Promise.reject('Failed request application')
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          waitChainApplications(_applicationIds, timeoutSeconds - 1).then(() => {
            resolve(undefined)
          }).catch((e) => {
            reject(e)
          })
        }, 1000)
      })
    }
  }
  return Promise.resolve(undefined)
}

const applicationSubscribed = async (applicationId: string) => {
  const subscribedCreatorChain = gql`
    query subscribedCreatorChain {
      subscribedCreatorChain
    }
  `

  try {
    const res = await window.linera?.request({
      method: 'linera_graphqlQuery',
      params: {
        publicKey: userStore.account,
        applicationId,
        query: {
          query: subscribedCreatorChain.loc?.source?.body,
          variables: {}
        }
      }
    })
    return graphqlResult.keyValue(res, 'subscribedCreatorChain') || false
  } catch (e) {
    console.log('Failed query subscribed application', e)
    return Promise.reject('Failed query subscribed application')
  }
}

const subscribeApplicationCreatorChain = async (applicationId: string) => {
  const subscribeCreatorChain = gql`
    mutation subscribeCreatorChain {
      subscribeCreatorChain
    }
  `

  try {
    const res = await window.linera?.request({
      method: 'linera_graphqlMutation',
      params: {
        publicKey: userStore.account,
        applicationId,
        query: {
          query: subscribeCreatorChain.loc?.source?.body,
          variables: {}
        }
      }
    })
    return graphqlResult.keyValue(res, 'subscribeCreatorChain')
  } catch (e) {
    console.log('Failed subscribe application', e)
    return Promise.reject('Failed subscribe application')
  }
}

const delay = async (milliSeconds: number) => {
  return new Promise((resolve) => {
    setTimeout(() => resolve(undefined), milliSeconds)
  })
}

const onAddLiquidity = async () => {
  if (!userStore.account) return
  if (!tokenZeroAmount.value || tokenZeroAmount.value < 0) {
    return
  }
  if (!tokenOneAmount.value || tokenOneAmount.value < 0) {
    return
  }
  if (!validateAmount()) return

  const applicationIds = await chainApplications()
  if (!applicationIds.includes(token0Id.value)) {
    await requestApplication(token0Id.value)
  }
  await delay(100)
  if (!applicationIds.includes(token1.value)) {
    await requestApplication(token1.value)
  }
  await delay(100)
  try {
    await waitChainApplications([token0Id.value, token1.value], 10)
  } catch (e) {
    console.log('Failed wait applications', e)
    return
  }
  await delay(100)
  if (!await applicationSubscribed(token0Id.value)) {
    await subscribeApplicationCreatorChain(token0Id.value)
  }
  await delay(100)
  if (!await applicationSubscribed(token1.value)) {
    await subscribeApplicationCreatorChain(token1.value)
  }
  await delay(100)

  await approveToSwap(token0Id.value, userStore.account, tokenZeroAmount.value.toString())
  await delay(100)
  await approveToSwap(token1.value, userStore.account, tokenOneAmount.value.toString())
  await delay(100)

  dbModel.ownerFromPublicKey(userStore.account).then(() => {
    walletStore.addLiquidity(
      token0Id.value || '',
      token1.value || '',
      userStore.account,
      tokenZeroAmount.value,
      tokenOneAmount.value
    ).then().catch((e) => {
      notificationStore.pushNotification({
        Title: 'Add liquidity',
        Message: e as string
      })
    })
  }).catch((e) => {
    notificationStore.pushNotification({
      Title: 'Invalid account',
      Message: e as string
    })
  })
}

watch(tokenZeroAmount, (amount) => {
  if (amount === null || amount < 0) {
    tokenZeroAmount.value = 0
  }
})

watch(tokenOneAmount, (amount) => {
  if (amount === null || amount < 0) {
    tokenOneAmount.value = 0
  }
})

const subscriptionHandler = (msg: unknown) => {
  const data = (graphqlResult.keyValue(msg, 'data') || []) as Record<string, Record<string, Record<string, Record<string, Record<string, unknown>>>>>
  if (data.result.notifications.reason.NewBlock) {
    const blockChainId = data.result.notifications.chain_id.toString()
    if (blockChainId === userStore.chainId) {
      block.blockHeight = data.result.notifications.reason.NewBlock.height as number
      block.blockHash = data.result.notifications.reason.NewBlock.hash as string
    }
  }
}

const refreshBalance = () => {
  if (!userStore.account) return

  dbModel.ownerFromPublicKey(userStore.account).then((v) => {
    walletStore.getBalance(token0Id.value, userStore.chainId, v, (error, balance) => {
      if (error) {
        return
      }
      outBalance.value = Number(balance)
      validateAmount()
    })
    walletStore.getBalance(token1.value, userStore.chainId, v, (error, balance) => {
      if (error) {
        return
      }
      inBalance.value = Number(balance)
      validateAmount()
    })
  }).catch((e) => {
    notificationStore.pushNotification({
      Title: 'Invalid account',
      Message: e as string
    })
  })
}

watch(() => block.blockHeight, () => {
  refreshBalance()
})

onMounted(() => {
  refreshBalance()
  if (subscriptionId.value) return
  window.linera?.request({
    method: 'linera_subscribe'
  }).then((_subscriptionId) => {
    subscriptionId.value = _subscriptionId as string
    window.linera.on('message', subscriptionHandler)
  }).catch((e) => {
    console.log('Fail subscribe', e)
  })
})

onUnmounted(() => {
  if (!subscriptionId.value) return
  void window.linera?.request({
    method: 'linera_unsubscribe',
    params: [subscriptionId.value]
  })
  subscriptionId.value = undefined as unknown as string
})

</script>

<style scoped lang='sass'>
.swap-amount-label
  font-size: 20px
  margin-right: 4px

.swap-amount-icon
  margin-right: 4px
  margin-top: 2px

:deep(.swap-token)
  .q-select
    .q-icon
      font-size: 16px

.swap-amount-input
  width: 100%

.exchange-symbol
  border: 2px solid $grey-4
  border-radius: 50%
  width: 28px
  height: 28px
  padding: 2px 5px

.exchange-separator
  width: calc(50% - 14px)
  margin-bottom: 12px
</style>
