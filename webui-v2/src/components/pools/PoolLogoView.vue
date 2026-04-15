<template>
  <div class='pool-logo-view row no-wrap items-center'>
    <pool-pair-logo
      :token0-logo='token0Logo'
      :token1-logo='token1Logo'
      :size='avatarSize'
      :overlap='logoOverlap'
      :border-width='logoBorderWidth'
    />
    <div class='pool-logo-copy q-ml-md column justify-center'>
      <div
        class='pool-logo-pair row no-wrap items-center text-bold'
        :class='{ "pool-logo-pair--nowrap": noWrap }'
        :style='{fontSize: poolNameFontSize}'
      >
        <div class='pool-logo-token pool-logo-token--start q-mr-sm'>{{ token0Ticker }}</div>
        /
        <div class='pool-logo-token pool-logo-token--end q-ml-sm'>{{ token1Ticker }}</div>
      </div>
      <div v-if='showChips' class='row q-mt-xs' style='margin-left: -4px;'>
        <q-chip dense class='bg-mining font-size-12'>Minable</q-chip>
        <q-chip dense class='bg-virtual font-size-12'>Virtual LP</q-chip>
        <q-chip v-if='showRank' dense class='bg-secondary font-size-12'>Trending #1</q-chip>
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { constants } from 'src/constant'
import { ams, meme } from 'src/stores/export'
import { computed, toRef } from 'vue'
import PoolPairLogo from './PoolPairLogo.vue'

interface Props {
  token0Application?: ams.Application
  token1Application?: ams.Application
  showRank?: boolean
  avatarSize?: string
  showChips?: boolean
  poolNameFontSize?: string
  noWrap?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  showRank: true,
  avatarSize: '66px',
  showChips: true,
  poolNameFontSize: '20px',
  noWrap: false,
})
const token0Application = toRef(props, 'token0Application')
const token1Application = toRef(props, 'token1Application')
const showRank = toRef(props, 'showRank')
const avatarSize = toRef(props, 'avatarSize')
const showChips = toRef(props, 'showChips')
const poolNameFontSize = toRef(props, 'poolNameFontSize')
const noWrap = toRef(props, 'noWrap')

const token0Logo = computed(() => ams.Ams.applicationLogo(token0Application.value || {} as ams.Application) || constants.LINERA_LOGO)
const token1Logo = computed(() => ams.Ams.applicationLogo(token1Application.value || {} as ams.Application) || constants.LINERA_LOGO)
const token0Meme = computed(() => JSON.parse(token0Application.value?.spec || '{}') as meme.Meme)
const token1Meme = computed(() => JSON.parse(token1Application.value?.spec || '{}') as meme.Meme)
const token0Ticker = computed(() => token0Meme.value?.ticker || constants.LINERA_TICKER)
const token1Ticker = computed(() => token1Meme.value?.ticker || constants.LINERA_TICKER)

const logoOverlap = computed(() => `${Math.round(Number(avatarSize.value.replace('px', '')) * 0.38)}px`)
const logoBorderWidth = computed(() => `${Math.max(2, Math.round(Number(avatarSize.value.replace('px', '')) * 0.06))}px`)

</script>

<style scoped lang='sass'>
.pool-logo-view
  min-width: 0

.pool-logo-copy
  min-width: 0
  flex: 1 1 auto

.pool-logo-pair
  min-width: 0

.pool-logo-pair--nowrap
  flex-wrap: nowrap

.pool-logo-token
  min-width: 0

.pool-logo-pair--nowrap .pool-logo-token
  overflow: hidden
  text-overflow: ellipsis
  white-space: nowrap
</style>
