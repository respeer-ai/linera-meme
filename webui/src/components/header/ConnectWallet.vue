<template>
  <q-btn flat rounded @click='onConnectClick'>
    <q-menu v-if='account?.length' anchor='bottom right' self='top right' :offset='[0, 8]'>
      <q-card flat>
        <div class='row flex justify-center items-center' :style='{margin: "36px 0 36px 0", fontSize: "28px"}'>
          <q-space />
          <div :style='{marginLeft: "8px"}'>
            {{ Number(accountBalance).toFixed(4) }}
          </div>
          <div :style='{margin: "8px 0 0 8px", fontSize: "12px"}'>
            TLINERA
          </div>
          <q-space />
        </div>
        <q-separator :style='{margin: "0 0 16px 0"}' />
        <div class='popup-padding'>
          <div class='row'>
            <div :style='{width: "24px"}'>
              <q-img :src='addressIcon' width='16px' height='16px' />
            </div>
            <div>
              <div class='text-grey-6'>
                Address
              </div>
              <div class='row'>
                <div class='text-bold'>
                  {{ shortid.shortId(account, 14) }}
                </div>
                <div :style='{marginLeft: "8px"}' class='cursor-pointer'>
                  <q-img :src='copyIcon' width='16px' height='16px' @click='copyToClipboard(account)' />
                </div>
              </div>
              <div class='text-grey-6'>
                {{ Number(accountBalance).toFixed(4) }}
              </div>
            </div>
          </div>
          <div class='row' :style='{margin: "12px 0 0 0"}'>
            <div :style='{width: "24px"}'>
              <q-img :src='microchainIcon' width='16px' height='16px' />
            </div>
            <div>
              <div class='text-grey-6'>
                Microchain
              </div>
              <div class='row'>
                <div class='text-bold'>
                  {{ shortid.shortId(chainId, 14) }}
                </div>
                <div :style='{marginLeft: "8px"}' class='cursor-pointer'>
                  <q-img :src='copyIcon' width='16px' height='16px' @click='copyToClipboard(chainId)' />
                </div>
              </div>
              <div class='text-grey-6'>
                {{ Number(chainBalance).toFixed(4) }}
              </div>
            </div>
          </div>
          <q-btn
            flat rounded class='bg-red-6 full-width text-white'
            @click='onLogoutClick'
            label='Logout'
            :style='{margin: "8px 0 0 0"}'
          />
          <div class='text-grey-6 text-center' :style='{margin: "8px 0 4px 0", fontSize: "12px"}'>
            Powered by CheCko
          </div>
        </div>
      </q-card>
    </q-menu>
    <q-img src='https://avatars.githubusercontent.com/u/107513858?s=48&v=4' width='24px' height='24px' />
    <div :style='{margin: "2px 0 0 8px"}' class='text-grey-9 text-bold'>
      {{ account?.length ? shortid.shortId(account, 6) : 'Connect Wallet' }} <span v-if='account?.length'><span class='text-grey-4'>|</span> {{ (Number(accountBalance) + Number(chainBalance)).toFixed(4) }}</span>
    </div>
  </q-btn>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Cookies } from 'quasar'
import { useUserStore } from 'src/mystore/user'
import { shortid, graphqlResult } from 'src/utils'
import { Web3 } from 'web3'
import { addressIcon, microchainIcon, copyIcon } from 'src/assets'
import { BALANCES } from 'src/graphql'
import { dbModel, rpcModel } from 'src/model'

const user = useUserStore()
const account = computed(() => user.account?.trim())
const chainId = computed(() => user.chainId?.trim())

const accountBalance = computed(() => user.accountBalance)
const chainBalance = computed(() => user.chainBalance)

const getProviderState = () => {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
  window.linera.request({
    method: 'metamask_getProviderState'
  }).then(async (result) => {
    user.chainId = ((result as Record<string, string>).chainId).substring(2)
    user.account = ((result as Record<string, string>).accounts)[0]
    Cookies.set('CheCko-Login-Account', user.account)
    Cookies.set('CheCko-Login-Microchain', user.chainId)
    await getBalances()
  }).catch((e) => {
    console.log('metamask_getProviderState', e)
  })
}

const onConnectClick = async () => {
  if (!window.linera) {
    return window.open('https://github.com/respeer-ai/linera-wallet.git')
  }

  try {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
    const web3 = new Web3(window.linera)
    await web3.eth.requestAccounts()
  } catch (e) {
    // DO NOTHING
  }

  getProviderState()
  await getBalances()
}

const onLogoutClick = () => {
  Cookies.remove('CheCko-Login-Account')
  Cookies.remove('CheCko-Login-Microchain')
  user.$reset()
}

const walletReadyCall = (f: () => void) => {
  if (!window.linera) {
    return setTimeout(() => walletReadyCall(f), 1000)
  }
  f()
}

const copyToClipboard = async (content: string) => {
  await navigator.clipboard.writeText(content)
}

onMounted(() => {
  walletReadyCall(() => {
    void getProviderState()
  })
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const getBalances = async () => {
  const owner = await dbModel.ownerFromPublicKey(account.value)
  // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
  window.linera.request({
    method: 'linera_graphqlQuery',
    params: {
      publicKey: account.value,
      query: {
        query: BALANCES.loc?.source?.body,
        variables: {
          chainOwners: Object.fromEntries(new Map([[chainId.value, [`User:${owner}`]]])),
          chainId: chainId.value,
          publicKey: account.value
        }
      }
    }
  }).then((result) => {
    const balances = graphqlResult.keyValue(result, 'balances') as rpcModel.Balances
    user.chainBalance = rpcModel.chainBalance(balances, chainId.value).toFixed(4)
    user.accountBalance = rpcModel.ownerBalance(balances, chainId.value, owner).toFixed(4)
  }).catch((e) => {
    console.log(e)
  })
}

</script>

<style lang='sass' scoped>
</style>
