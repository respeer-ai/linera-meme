<template>
  <div>
    <div class='text-neutral font-size-24 text-center'>Connect Wallet</div>
    <div class='q-pa-md q-mb-lg q-mt-md'>
      <q-btn no-caps class='q-pa-md bg-dark radius-16 full-width' @click='onCheCkoClick' :disabled='!cheCkoInstalled'>
        <div class='row items-center full-width q-py-sm'>
          <q-img :src='constants.CHECKO_LOGO' width='32px' height='32px' />
          <div class='q-ml-md font-size-16'>{{ user.WalletType.CheCko }}</div>
        </div>
      </q-btn>
      <q-btn no-caps class='q-pa-md bg-dark radius-16 full-width q-mt-sm' @click='onMetamaskClick' :disabled='!metamaskInstalled'>
        <div class='row items-center full-width q-py-sm'>
          <q-img :src='constants.METAMASK_LOGO' width='32px' height='32px' />
          <div class='q-ml-md font-size-16'>{{ user.WalletType.Metamask }}</div>
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
import { Wallet } from 'src/wallet'

const cheCkoInstalled = ref(false)
const metamaskInstalled = ref(false)

const emit = defineEmits<{
  (e: 'done'): void
  (e: 'error', error: string): void
}>()

const onConnectWallet = async (walletType: user.WalletType) => {
  try {
    await Wallet.connect(walletType)
    emit('done')
  } catch (e) {
    emit('error', JSON.stringify(e))
  }
}

const onCheCkoClick = async () => {
  onConnectWallet(user.WalletType.CheCko)
}

const onMetamaskClick = async () => {
  onConnectWallet(user.WalletType.Metamask)
}

const updateWalletState = () => {
  cheCkoInstalled.value = window.linera !== undefined
  metamaskInstalled.value = window.ethereum !== undefined
}

onMounted(async () => {
  try {
    await Wallet.waitOnReady()
  } catch {
    // DO NOTHING
  }
  updateWalletState()
})

</script>