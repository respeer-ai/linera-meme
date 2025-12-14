<template>
  <div>
    <q-btn rounded class='bg-primary flex justify-center items-center hover-primary' @click='onConnectClick' :loading='waiting'>
      <div class='row flex justify-center items-center'>
        <q-icon v-if='showIcon' name='wallet' />
        <span :class='[ showIcon ? "q-ml-sm" : "", "q-header-line" ]'>{{ label }}</span>
      </div>
    </q-btn>
  </div>
  <q-dialog v-model='connecting'>
    <div class='bg-dark-secondary q-pt-lg q-pb-xl radius-16' style='min-width: 400px;'>
      <connect-wallet-view @done='connecting = false' @error='connecting = false' />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { onMounted, ref, toRef } from 'vue'
import { Wallet } from 'src/wallet'

import ConnectWalletView from './ConnectWalletView.vue'

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

const connecting = ref(false)
const waiting = ref(true)

const onConnectClick = () => {
  connecting.value = true
}

onMounted(async () => {
  await Wallet.waitOnReady()
  waiting.value = false
})

</script>

<style scoped lang='sass'>
::v-deep(.q-btn)
  .q-icon.material-icons
    color: white
</style>
