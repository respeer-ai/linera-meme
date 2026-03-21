<template>
  <q-layout view='lHh Lpr lff' class='bg-dark non-selectable'>
    <q-header class='bg-dark'>
      <q-toolbar class='q-py-md'>
        <header-view class='fill-parent-width' />
      </q-toolbar>
    </q-header>

    <q-page-container class='bg-glass bg-dark'>
      <div class='flex items-center justify-center'>
        <div v-if='!walletConnected' class='q-mt-lg page-width'>
          <wallet-tip-view />
        </div>
      </div>
      <router-view />
    </q-page-container>

    <q-footer class='bg-dark'>
      <q-card flat class='bg-dark-secondary flex justify-center q-mt-xl q-pt-xl q-pb-lg'>
        <div class='page-width'>
          <footer-view />
        </div>
      </q-card>
    </q-footer>
  </q-layout>
</template>

<script setup lang='ts'>
import initWasm from '../../dist/wasm/linera_wasm'
import wasmModuleUrl from '../../dist/wasm/linera_wasm_bg.wasm?url'
import { computed, onMounted } from 'vue'
import { notify, user } from 'src/stores/export'

import HeaderView from 'src/components/header/HeaderView.vue'
import FooterView from 'src/components/footer/FooterView.vue'
import WalletTipView from 'src/components/wallet/WalletTipView.vue'

onMounted(async () => {
  await initWasm(await fetch(wasmModuleUrl))
  notify.Notify.subscribe()
})

const walletConnected = computed(() => user.User.walletConnected())

</script>
