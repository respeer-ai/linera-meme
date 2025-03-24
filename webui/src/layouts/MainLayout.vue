<template>
  <q-layout view='hHh Lpr lFf'>
    <q-header>
      <q-toolbar class='text-white bg-white vertical-menu-padding shadow-2'>
        <Header class='full-width' />
      </q-toolbar>
    </q-header>
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang='ts'>
import { onMounted } from 'vue'
import { notification } from 'src/mystore'

import Header from 'src/components/header/Header.vue'

const _notification = notification.useNotificationStore()

onMounted(() => {
  _notification.$subscribe((_, state) => {
    state.Notifications.forEach((notif, index) => {
      if (notif.Popup) {
        state.Notifications.splice(index, 1)
        notification.notify(notif)
      }
    })
  })
})

</script>
