<template>
  <div>
    <q-input
      filled
      placeholder='Search tokens or liquidity pools'
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

<style scoped lang='sass'>

::v-deep(.q-input)
  .q-field--dark,
  .q-field--light,
  .q-field--filled,
  .q-field__control
    background-color: #FFFFFF05
  .q-field__native
    color: var(--q-neutral-twenty-five) !important

.material-icons
  color: var(--q-neutral-twenty-five)

</style>
