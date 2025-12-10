<template>
  <q-layout view='lHh Lpr lFf' class='bg-dark bg-glass'>
    <q-header class='bg-dark'>
      <q-toolbar class='q-py-md'>
        <header-view class='fill-parent-width' />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang='ts'>

import HeaderView from 'src/components/header/HeaderView.vue'

</script>
