<template>
  <div
    class='row items-center radius-12 q-px-sm hover-primary border-neutral-25'
    :style='{
      width: expanded ? "220px" : "40px",
      height: "40px",
      overflow: "hidden",
      transition: "width .25s"
    }'
  >
    <q-icon
      name='search'
      size='20px'
      class='cursor-pointer'
      @click='onSearchClick'
    />

    <q-input
      v-if='expanded'
      dense
      filled
      borderless
      placeholder='Search tokens or liquidity pools'
      v-model='searchText'
      class='q-ml-sm col'
      @keyup.enter='onSearch'
    />

    <q-icon
      v-if='expanded'
      name='close'
      size='18px'
      class='cursor-pointer'
      @click='onSearchCloseClick'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue'

const searchText = ref('')
const expanded = ref(false)

const onSearchClick = () => {
  expanded.value = true
}

const onSearchCloseClick = () => {
  expanded.value = false
}

const emit = defineEmits<{
  (ev: 'search', keyword: string): void
}>()

const onSearch = () => {
  emit('search', searchText.value)
}

</script>

<style scoped lang='sass'>

::v-deep(.q-input)
  .q-field--dark,
  .q-field--light,
  .q-field--filled,
  .q-field__control
    background-color: transparent
  .q-field__native
    color: var(--q-neutral-twenty-five) !important

.material-icons
  color: var(--q-neutral-twenty-five)

::v-deep(.q-input)
  .q-field__control,
  .q-field__native,
  .q-field__marginal
    min-height: 40px
    height: 40px
  .q-field__suffix,
  .q-field__prepend
    line-height: 32px

</style>
