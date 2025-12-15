<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
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
    Wallet.getProviderState()
  }
}

const handleNativeNotification = (msg: unknown) => {
  const _msg = msg as Record<string, Record<string, unknown>>
  if (_msg.reason?.NewBlock) {
    Wallet.getProviderState()
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
  user.User.setWalletConnecting(true)
  user.User.setBalanceUpdating(true)

  await Wallet.waitOnReady()
  await nextTick()

  try {
    await Wallet.getProviderState(user.WalletType.CheCko)
    user.User.setWalletConnecting(false)
    await Wallet.getBalance()
  } catch (e) {
    console.log(`Failed get CheCko wallet state: `, e)
  }

  try {
    await Wallet.getProviderState(user.WalletType.Metamask)
    user.User.setWalletConnecting(false)
    console.log(111)
    await Wallet.getBalance()
    console.log(222)
  } catch (e) {
    console.log(`Failed get CheCko wallet state: `, e)
  }

  user.User.setWalletConnecting(false)
  user.User.setBalanceUpdating(false)
}

onMounted(async () => {
  await getWalletsState()
})

onUnmounted(() => {
  if (subscriptionId.value) {
    Wallet.unsubscribe(subscriptionId.value)
    subscriptionId.value = undefined as unknown as string
  }
})

</script>
