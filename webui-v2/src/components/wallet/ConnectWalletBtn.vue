<template>
  <div>
    <q-btn rounded class='bg-primary flex justify-center items-center hover-primary' @click='onConnectClick'>
      <div class='row flex justify-center items-center'>
        <q-icon v-if='showIcon' name='wallet' />
        <span :class='[ showIcon ? "q-ml-sm" : "", "q-header-line" ]'>{{ label }}</span>
      </div>
    </q-btn>
  </div>
  <q-dialog v-model='connecting'>
    <div class='bg-dark-secondary q-pt-lg q-pb-xl radius-16' style='min-width: 400px;'>
      <connect-wallet-view />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { ref, toRef } from 'vue'

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

const onConnectClick = () => {
  connecting.value = true
}

</script>

<style scoped lang='sass'>
::v-deep(.q-btn)
  .q-icon.material-icons
    color: white
</style>
