<template>
  <div>
    <div class='text-neutral font-size-24 text-center'>Connect Wallet</div>
    <div class='q-pa-md q-mb-lg q-mt-md'>
      <q-btn no-caps class='q-pa-md bg-dark radius-16 full-width' @click='onCheCkoClick' :disabled='!cheCkoInstalled'>
        <div class='row items-center full-width q-py-sm'>
          <q-img :src='constants.CHECKO_LOGO' width='32px' height='32px' />
          <div class='q-ml-md font-size-16'>{{ user.WalletConnectType.CheCko }}</div>
        </div>
      </q-btn>
      <q-btn no-caps class='q-pa-md bg-dark radius-16 full-width q-mt-sm' @click='onMetamaskClick' :disabled='!metamaskInstalled'>
        <div class='row items-center full-width q-py-sm'>
          <q-img :src='constants.METAMASK_LOGO' width='32px' height='32px' />
          <div class='q-ml-md font-size-16'>{{ user.WalletConnectType.Metamask }}</div>
        </div>
      </q-btn>
    </div>
    <q-separator />
    <div class='q-mt-md text-center text-neutral'>By logging in, you agree to our <a class='text-light-blue cursor-pointer'>Term of Use</a></div>
  </div>
</template>

<script setup lang='ts'>
import { constants } from 'src/constant'
import { user } from 'src/stores/export'
import { onMounted, ref } from 'vue'
import { Web3 } from 'web3'
import { getProviderState, walletReadyCall } from './GetWalletInfo'
import * as metamask from '@linera/metamask'

const cheCkoInstalled = ref(false)
const metamaskInstalled = ref(false)

const onCheCkoClick = async () => {
  if (!window.linera) {
    return window.open('https://github.com/respeer-ai/linera-wallet.git')
  }

  try {
    const web3 = new Web3(window.linera)
    await web3.eth.requestAccounts()
  } catch {
    // DO NOTHING
  }

  getProviderState(window.linera, user.WalletConnectType.CheCko)
}

const onMetamaskClick = async () => {
  if (!window.ethereum) {
    return window.open('https://chromewebstore.google.com/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn?hl=zh-CN&utm_source=ext_sidebar')
  }

  new metamask.Signer()

  getProviderState(window.ethereum, user.WalletConnectType.Metamask)
}

const updateWalletState = () => {
  cheCkoInstalled.value = window.linera !== undefined
  metamaskInstalled.value = window.ethereum !== undefined
}

onMounted(() => {
  walletReadyCall(() => {
    updateWalletState()
  })
})

</script>