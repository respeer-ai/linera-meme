<template>
  <div>
    <q-btn rounded class='bg-primary flex justify-center items-center'>
      <div class='row flex justify-center items-center'>
        <q-icon v-if='showIcon' name='wallet' />
        <span :class='[ showIcon ? "q-ml-sm" : "", "q-header-line" ]'>{{ label }}</span>
      </div>
    </q-btn>
  </div>
</template>

<script setup lang='ts'>
import { toRef } from 'vue'

interface Props {
  label?: string
  showIcon?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  label: 'Connect Wallet',
  showIcon: true
})
const label = toRef(props, 'label')
const showIcon = toRef(props, 'showIcon')

</script>

<style scoped lang='sass'>
::v-deep(.q-btn)
  .q-icon.material-icons
    color: white
</style>
