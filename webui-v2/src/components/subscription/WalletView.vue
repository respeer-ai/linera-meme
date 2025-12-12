<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { user } from 'src/stores/export'
import { Wallet } from 'src/wallet'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

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

onMounted(() => {
  Wallet.waitOnReady(() => {
    Wallet.getProviderState(async () => {
      await Wallet.connect(user.WalletType.Metamask, () => {
        Wallet.getProviderState()
      }, (e) => {
        console.log('Failed connect metamask', e)
      })
    })
  })
})

onUnmounted(() => {
  if (subscriptionId.value) {
    Wallet.unsubscribe(subscriptionId.value)
    subscriptionId.value = undefined as unknown as string
  }
})

</script>
