<template>
  <q-layout view='lHh Lpr lff' class='bg-dark'>
    <q-header class='bg-dark'>
      <q-toolbar class='q-py-md'>
        <header-view class='fill-parent-width' />
      </q-toolbar>
    </q-header>

    <q-page-container class='bg-glass bg-dark'>
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
import { onMounted } from 'vue'
import { notify } from 'src/stores/export'

import HeaderView from 'src/components/header/HeaderView.vue'
import FooterView from 'src/components/footer/FooterView.vue'

onMounted(async () => {
  await initWasm(await fetch(wasmModuleUrl))
  notify.Notify.subscribe()
})

</script>
