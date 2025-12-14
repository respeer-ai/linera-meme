<template>
  <div>
    <q-input
      filled
      v-model='searchText'
    >
      <template #prepend>
        <q-icon name='search' />
      </template>
    </q-input>
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue'

const searchText = ref('')

</script>
