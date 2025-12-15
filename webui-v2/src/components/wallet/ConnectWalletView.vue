<template>
  <div>
    <div class='text-neutral font-size-24 text-center'>Connect Wallet</div>
    <div class='q-pa-md q-mb-lg q-mt-md'>
      <q-btn no-caps class='q-pa-md bg-dark radius-16 full-width' @click='onCheCkoClick' :disabled='!cheCkoInstalled || disabled'>
        <div class='row items-center full-width q-py-sm'>
          <q-img :src='constants.CHECKO_LOGO' width='32px' height='32px' />
          <div class='q-ml-md font-size-16'>{{ user.WalletType.CheCko }}</div>
          <q-space />
          <q-spinner-ios v-if='cheCkoConnecting' color='primary' size='1em' />
        </div>
      </q-btn>
      <q-btn no-caps class='q-pa-md bg-dark radius-16 full-width q-mt-sm' @click='onMetamaskClick' :disabled='!metamaskInstalled || disabled'>
        <div class='row items-center full-width q-py-sm'>
          <q-img :src='constants.METAMASK_LOGO' width='32px' height='32px' />
          <div class='q-ml-md font-size-16'>{{ user.WalletType.Metamask }}</div>
          <q-space />
          <q-spinner-ios v-if='metaMaskConnecting' color='primary' size='1em' />
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
import { computed, onMounted, ref } from 'vue'
import { Wallet } from 'src/wallet'

const cheCkoInstalled = ref(false)
const metamaskInstalled = ref(false)

const cheCkoConnecting = ref(false)
const metaMaskConnecting = ref(false)

const disabled = computed(() => cheCkoConnecting.value || metaMaskConnecting.value)

const emit = defineEmits<{
  (e: 'done'): void
  (e: 'error', error: string): void
}>()

const getWalletsState = async (walletType: user.WalletType) => {
  try {
    user.User.setWalletConnecting(true)
    await Wallet.getProviderState(walletType)
    user.User.setBalanceUpdating(true)
    user.User.setWalletConnecting(false)
    await Wallet.getBalance()
    user.User.setBalanceUpdating(false)
    return
  } catch (e) {
    console.log(`Failed get ${walletType} wallet state: `, e)
  }
}

const onConnectWallet = async (walletType: user.WalletType) => {
  try {
    await Wallet.connect(walletType)
    await getWalletsState(walletType)
    emit('done')
  } catch (e) {
    emit('error', JSON.stringify(e))
  }
}

const onCheCkoClick = async () => {
  cheCkoConnecting.value = true
  await onConnectWallet(user.WalletType.CheCko)
  cheCkoConnecting.value = false
}

const onMetamaskClick = async () => {
  metaMaskConnecting.value = true
  await onConnectWallet(user.WalletType.Metamask)
  metaMaskConnecting.value = false
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