<template>
  <div
    class='pool-pair-logo'
    :style='{
      "--pool-pair-logo-size": size,
      "--pool-pair-logo-overlap": overlap,
      "--pool-pair-logo-border-width": borderWidth,
    }'
  >
    <q-avatar class='pool-pair-logo-token pool-pair-logo-token-back'>
      <q-img :src='token1Logo' fit='contain' />
    </q-avatar>
    <q-avatar class='pool-pair-logo-token pool-pair-logo-token-front'>
      <q-img :src='token0Logo' fit='contain' />
    </q-avatar>
  </div>
</template>

<script setup lang='ts'>
interface Props {
  token0Logo: string
  token1Logo: string
  size?: string
  overlap?: string
  borderWidth?: string
}

withDefaults(defineProps<Props>(), {
  size: '30px',
  overlap: '10px',
  borderWidth: '2px',
})
</script>

<style scoped lang='sass'>
.pool-pair-logo
  position: relative
  width: calc(var(--pool-pair-logo-size) + var(--pool-pair-logo-overlap))
  height: var(--pool-pair-logo-size)
  flex: 0 0 auto

.pool-pair-logo-token
  position: absolute
  top: 0
  width: var(--pool-pair-logo-size)
  height: var(--pool-pair-logo-size)
  border: var(--pool-pair-logo-border-width) solid rgba(16, 18, 24, 0.88)
  background: rgba(255, 255, 255, 0.1)

.pool-pair-logo-token-front
  left: 0
  z-index: 2

.pool-pair-logo-token-back
  left: var(--pool-pair-logo-overlap)
</style>
