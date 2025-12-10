<template> 
  <div>
    <q-btn flat dense round icon='invert_colors' @click='onModeSwitchClick' />
  </div>
</template>

<script lang='ts' setup>
import { Dark } from 'quasar'

const onModeSwitchClick = () => {
  Dark.toggle()
}

</script>
