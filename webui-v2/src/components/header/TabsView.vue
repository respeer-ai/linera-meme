<template>
  <q-tabs
    v-model='tab'
    indicator-color='transparent'
  >
    <q-tab :name='Tab.Trade' :label='Tab.Trade' />
    <q-tab :name='Tab.Tokens' :label='Tab.Tokens' />
    <q-tab :name='Tab.LeaderBoard' :label='Tab.LeaderBoard' />
    <q-tab :name='Tab.Create' :label='Tab.Create' />
    <q-tab :name='Tab.Docs' :label='Tab.Docs' />
  </q-tabs>
</template>

<script setup lang='ts'>
import { ref } from 'vue'

enum Tab {
  Trade = 'Trade',
  Tokens = 'Tokens',
  LeaderBoard = 'Leader Board',
  Create = 'Create',
  Docs = 'Docs'
}

const tab = ref(Tab.Trade)

</script>
