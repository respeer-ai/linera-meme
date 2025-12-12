<template>
  <div>
    <q-select
      filled
      v-model='network'
      :options='networks'
    >
      <template #prepend>
        <q-img :src='constants.LINERA_LOGO' width='24px' height='24px' />
      </template>
    </q-select>
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { constants } from 'src/constant'

enum Network {
  TestnetConway = 'Testnet Conway',
  Mainnet = 'Mainnet (WIP)'
}

const networks = ref([{
  label: Network.TestnetConway,
  value: Network.TestnetConway
}, {
  label: Network.Mainnet,
  value: Network.Mainnet,
  disable: true
}])
const network = ref(Network.TestnetConway)

</script>
