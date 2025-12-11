<template>
  <div class='bg-transparent text-transparent' style='height: 1px; width: 1px;'>
    <pools-view />
    <applications-view />
    <memes-view />
    <wallet-view />
  </div>
</template>

<script setup lang='ts'>

import PoolsView from './PoolsView.vue'
import ApplicationsView from './ApplicationsView.vue'
import MemesView from './MemesView.vue'
import WalletView from './WalletView.vue'

</script>
