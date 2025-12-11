<template>
  <div>
    <q-btn rounded class='bg-primary flex justify-center items-center hover-primary' @click='onConnectClick'>
      <div class='row flex justify-center items-center'>
        <q-icon v-if='showIcon' name='wallet' />
        <span :class='[ showIcon ? "q-ml-sm" : "", "q-header-line" ]'>{{ label }}</span>
      </div>
    </q-btn>
  </div>
</template>

<script setup lang='ts'>
import { Cookies } from 'quasar'
import { computed, onMounted, toRef } from 'vue'
import { account, user } from 'src/stores/export'
import { dbModel, rpcModel } from 'src/model'
import { BALANCES } from 'src/graphql'
import { Web3 } from 'web3'

interface Props {
  label?: string
  showIcon?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  label: 'Connect Wallet',
  showIcon: true
})
const label = toRef(props, 'label')
const showIcon = toRef(props, 'showIcon')

const publicKey = computed(() => user.User.publicKey())
const chainId = computed(() => user.User.chainId())

const getBalances = async () => {
  if (!publicKey.value) return
  const owner = await dbModel.ownerFromPublicKey(publicKey.value)
  window.linera.request({
    method: 'linera_graphqlQuery',
    params: {
      publicKey: publicKey.value,
      query: {
        query: BALANCES.loc?.source?.body,
        variables: {
          chainOwners: [{
            chainId: chainId.value,
            owners: [account._Account.formalizeOwner(owner)]
          }],
          chainId: chainId.value,
          publicKey: publicKey.value
        }
      }
    }
  }).then((result) => {
    const balances = result as rpcModel.Balances
    user.User.setChainBalance(rpcModel.chainBalance(balances, chainId.value))
    user.User.setAccountBalance(rpcModel.ownerBalance(balances, chainId.value, account._Account.formalizeOwner(owner)))
  }).catch((e) => {
    console.log(e)
  })
}

const getProviderState = () => {
  window.linera.request({
    method: 'metamask_getProviderState'
  }).then(async (result) => {
    user.User.setChainId(((result as Record<string, string>)?.chainId)?.substring(2) as string)
    user.User.setPublicKey(((result as Record<string, string>)?.accounts)?.[0] as string)
    user.User.setWalletConnectedType(user.WalletConnectType.CheCko)

    Cookies.set('CheCko-Login-Account', user.User.publicKey())
    Cookies.set('CheCko-Login-Microchain', user.User.chainId())
    await getBalances()
  }).catch((e) => {
    console.log('metamask_getProviderState', e)
  })
}

const walletReadyCall = (f: () => void) => {
  if (!window.linera && !window.ethereum) {
    return setTimeout(() => walletReadyCall(f), 1000)
  }
  f()
}

onMounted(() => {
  walletReadyCall(() => {
    void getProviderState()
  })
})

const onConnectClick = async () => {
  if (!window.linera) {
    return window.open('https://github.com/respeer-ai/linera-wallet.git')
  }

  try {
    const web3 = new Web3(window.linera)
    await web3.eth.requestAccounts()
  } catch {
    // DO NOTHING
  }

  getProviderState()
  await getBalances()
}

</script>

<style scoped lang='sass'>
::v-deep(.q-btn)
  .q-icon.material-icons
    color: white
</style>
