<template>
  <div class='row'>
    <q-space />
    <div class='text-center'>
      <div class='text-neutral'>1D Volume</div>
      <div class='font-size-24 text-bold'>{{ (Number(protocolStat?.volume) || 0).toFixed(4) }} TLINERA</div>
      <div class='row'>
        <q-space />
        <q-icon
          v-if='shouldDisplayDirectionIcon(volumeDirection())'
          :name='directionIcon(volumeDirection())'
          :color='directionIconColor(volumeDirection())'
          size='16px' 
        />
        <div>{{ (protocolStat?.volume_change || 0.0).toFixed(2) }}% today</div>
        <q-space />
      </div>
    </div>
    <q-space />
    <div class='text-center'>
      <div class='text-neutral'>Protocol TVL</div>
      <div class='font-size-24 text-bold'>{{ (Number(protocolStat?.tvl) || 0).toFixed(4) }} TLINERA</div>
      <div class='row'>
        <q-space />
        <q-icon
          v-if='shouldDisplayDirectionIcon(tvlDirection())'
          :name='directionIcon(tvlDirection())'
          :color='directionIconColor(tvlDirection())'
          size='16px' 
        />
        <div>{{ (protocolStat?.tvl_change || 0.0).toFixed(2) }}% today</div>
        <q-space />
      </div>
    </div>
    <q-space />
  </div>
</template>

<script setup lang='ts'>
import { kline } from 'src/stores/export'
import { computed, onMounted } from 'vue'

const protocolStat = computed(() => kline.Kline.protocolStat())

onMounted(async () => {
  await kline.Kline.getProtocolStat()
})

enum Direction {
  UP = 'Up',
  DOWN = 'Down',
  SAME = 'Same'
}

const volumeDirection = () => {
  if (!protocolStat.value) return Direction.SAME
  return Number(protocolStat.value.volume_change) > 0 ? Direction.UP : Number(protocolStat.value.volume_change) < 0 ? Direction.DOWN : Direction.SAME
}

const tvlDirection = () => {
  if (!protocolStat.value) return Direction.SAME
  return Number(protocolStat.value.tvl_change) > 0 ? Direction.UP : Number(protocolStat.value.tvl_change) < 0 ? Direction.DOWN : Direction.SAME
}

const shouldDisplayDirectionIcon = (direction: Direction) => {
  return Direction.SAME === direction ? false : true
}

const directionIcon = (direction: Direction) => {
  return direction ===  Direction.UP ? 'arrow_drop_up' : direction ===  Direction.DOWN ? 'arrow_drop_down' : ''
}

const directionIconColor = (direction: Direction) => {
  return direction ===  Direction.UP ? 'green-4' : direction ===  Direction.DOWN ? 'red-4' : 'blue-4'
}

</script>
