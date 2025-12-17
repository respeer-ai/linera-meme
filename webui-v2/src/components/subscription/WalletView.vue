<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { Cookies } from 'quasar'
import { user } from 'src/stores/export'
import { Wallet } from 'src/wallet'
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'

const walletConnected = computed(() => user.User.walletConnected())

const subscriptionId = ref(undefined as unknown as string)

watch(walletConnected, () => {
  Wallet.subscribe((_subscriptionId: string) => {
    subscriptionId.value = _subscriptionId
  }, subscriptionHandler)
})

const handleCheCkoNotification = (msg: unknown) => {
  const _msg = msg as Record<string, unknown>
  const data = _msg.data as Record<string, Record<string, Record<string, Record<string, Record<string, unknown>>>>>
  if (data?.result?.notifications?.reason?.NewBlock) {
    void Wallet.getProviderState()
    void Wallet.getBalance()
  }
}

const handleNativeNotification = (msg: unknown) => {
  const _msg = msg as Record<string, Record<string, unknown>>
  if (_msg.reason?.NewBlock) {
    void Wallet.getProviderState()
    void Wallet.getBalance()
  }
}

const subscriptionHandler = (walletType: user.WalletType, msg: unknown) => {
  switch (walletType) {
    case user.WalletType.CheCko:
      return handleCheCkoNotification(msg)
    case user.WalletType.Metamask:
      return handleNativeNotification(msg)
  }
}

const getWalletsState = async () => {
  await Wallet.waitOnReady()
  await nextTick()

  const lastWalletType = Cookies.get(user.WalletCookie.WalletConnectType) as user.WalletType
  if (!lastWalletType) return

  const walletTypes = lastWalletType ? [lastWalletType] : []
  walletTypes.push(...user.WalletTypes.filter((el) => !lastWalletType || el !== lastWalletType))

  let connected = false

  for (const walletType of walletTypes) {
    try {
      user.User.setWalletConnecting(true)
      await Wallet.getProviderState(walletType)

      connected = true

      break
    } catch (e) {
      console.log(`Failed get ${walletType} wallet state: `, e)
    }
  }

  user.User.setWalletConnecting(false)

  if (!connected) return
  
  user.User.setBalanceUpdating(true)

  try {
    await Wallet.getBalance()
  } catch (e) {
    console.log(`Failed get ${user.User.walletConnectedType()} wallet balance: `, e)
  }
  user.User.setBalanceUpdating(false)
}

onMounted(async () => {
  try {
    await getWalletsState()
  } catch {
    // DO NOTHING
  }
})

onUnmounted(() => {
  if (subscriptionId.value) {
    Wallet.unsubscribe(subscriptionId.value)
    subscriptionId.value = undefined as unknown as string
  }
})

</script>
