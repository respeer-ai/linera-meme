<template>
  <div class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md'>
    <div class='row'>
      <div class='font-size-16 text-bold'>{{ action }}</div>
      <q-space />
      <q-select
        :options='_tokens'
        v-model='token'
        class='bg-primary-twenty-five radius-16'
        style='overflow: hidden;'
      >
        <template #option='scope'>
          <q-item dense v-bind='scope.itemProps' class='items-center'>
            <q-avatar size='24px'>
              <q-img :src='ams.Ams.applicationLogo(scope.opt as ams.Application) || constants.LINERA_LOGO' width='24px' height='24px' fit='contain' />
            </q-avatar>
            <div class='q-ml-md'>
              <div class='row'>
                <div class='text-neutral text-bold'>
                  {{ scope.opt.meme?.ticker }}
                </div>
                <q-space />
              </div>
            </div>
          </q-item>
        </template>
        <template #selected>
          <div class='row'>
            <q-avatar size='24px' class='q-ml-xs'>
              <q-img :src='tokenLogo' width='24px' height='24px' fit='contain' />
            </q-avatar>
            <div class='swap-token-name text-bold swap-token-label flex items-center justify-center q-ml-sm'>
              {{ tokenTicker }}
            </div>
          </div>
        </template>
      </q-select>
    </div>
    <q-input v-model='amount' type='number' class='font-size-36 text-neutral text-bold' placeholder='0' :autofocus='autoFocus' :disable='disable' />
    <div class='q-mt-sm row'>
      <div class='font-size-16 text-neutral'>$ 0</div>
      <q-space />
      <div class='font-size-16 text-neutral flex items-center'>
        <span v-if='updatingBalance'>
          <q-spinner-hourglass
            color='neutral'
            size='1em'
            class='q-mb-xs'
          />
        </span>
        <span v-else>
          {{ balance }}
        </span>

        <span class='q-ml-sm'>{{ tokenTicker }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted, onUnmounted, ref, toRef, watch, watchEffect } from 'vue'
import { TokenAction } from './TokenAction'
import { Token } from './Token'
import { ams, meme, proxy, user } from 'src/stores/export'
import { constants } from 'src/constant'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'
import { Subscription } from 'src/subscription'
import { throttle } from 'lodash-es'

interface Props {
  action?: TokenAction
  autoFocus?: boolean
  tokens: Token[]
  disable?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  action: TokenAction.Sell,
  autoFocus: true,
  disable: false
})
const action = toRef(props, 'action')
const autoFocus = toRef(props, 'autoFocus')
const tokens = toRef(props, 'tokens')
const disable = toRef(props, 'disable')

interface TokenItem extends Token {
  label: string
  value: string
}
const _tokens = computed(() => tokens.value.map((el) => {
  return  {
    ...el,
    label: el.meme.ticker,
    value: el.meme.ticker
  } as TokenItem
}))

const token = defineModel<Token>()
const tokenLogo = computed(() => ams.Ams.applicationLogo(token.value as ams.Application) || constants.LINERA_LOGO)
const tokenTicker = computed(() => token.value?.meme?.ticker || constants.LINERA_TICKER)
const tokenApplicationId = computed(() => token.value?.applicationId || constants.LINERA_NATIVE_ID)

const amount = defineModel<string>('amount')
const balance = ref('0')
const nativeBalance = computed(() => user.User.balance())
const proxyBlockHash = computed(() => proxy.Proxy.blockHash())

const tokenChain = computed(() => proxy.Proxy.tokenCreatorChain(tokenApplicationId.value) as Chain)
const tokenApplication = computed(() => {
  return {
    chain_id: tokenChain.value?.chainId as string,
    owner: tokenChain.value?.token as string
  }
})

watch(nativeBalance, () => {
  if (tokenApplicationId.value === constants.LINERA_NATIVE_ID) {
    balance.value = nativeBalance.value
  }
})

const walletConnected = computed(() => user.User.walletConnected())
const updatingBalance = ref(false)

const getBalance = async () =>{
  if (!walletConnected.value) return

  if (tokenApplicationId.value !== constants.LINERA_NATIVE_ID) {
    updatingBalance.value = true
    await meme.MemeWrapper.balanceOfMeme(tokenApplication.value, (_balance: string) => {
      balance.value = Number(_balance).toFixed(4)
      updatingBalance.value = false
    }, () => {
      updatingBalance.value = false
    })
  } else {
    balance.value = nativeBalance.value
  }
}

const subscription = ref(undefined as unknown as Subscription)

const getBalanceThrottle = throttle(async () => {
  await getBalance()
}, 10000, {
  leading: true, 
  trailing: true
})

watch(proxyBlockHash, async () => {
  getBalanceThrottle()
})

watchEffect(() => {
  if (!walletConnected.value) return

  getBalanceThrottle()

  if (subscription.value) {
    subscription.value.unsubscribe()
  }

  if (tokenApplication.value && tokenChain.value && tokenApplicationId.value && walletConnected.value) {
    subscription.value = new Subscription(
      meme.MemeWrapper.applicationUrl(tokenApplication.value) as string,
      constants.PROXY_WS_URL,
      tokenChain.value.chainId,
      (height: number, hash: string) => {
        console.log(`New block height ${height} hash ${hash} on meme chain ${tokenApplicationId.value}`)
        getBalanceThrottle()
      }
    )
  }
})

onMounted(() => {
  token.value = tokens.value[0]
  proxy.Proxy.getMemeApplications(() => {
    getBalanceThrottle()
  })
})

onUnmounted(() => {
  if (subscription.value) {
    subscription.value.unsubscribe()
    subscription.value = undefined as unknown as Subscription
  }
})

</script>

<style scoped lang='sass'>
::v-deep(.q-input)
  .q-field__native,
  .q-field__control
    border-radius: 0
  .q-field__control:hover
    background-color: none !important
    background: none !important

::v-deep(.q-select)
  line-height: 32px
  .q-field__marginal
    height: 32px
  .q-field--auto-height
    min-height: 32px
  .q-field__control
    min-height: 32px
    height: 32px
  .q-field__native
    min-height: 32px
    padding: 0
</style>
