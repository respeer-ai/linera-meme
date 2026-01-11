<template>
  <div class='row'>
    <div class='row'>
      <div class='bg-primary-25 border-primary-50 row q-pa-xs' :style='{ borderRadius: "32px", width: avatarSize, height: avatarSize }'>
        <div :style='{ width: halfImageSize, overflow: "hidden", borderTopLeftRadius: halfImageSize, borderBottomLeftRadius: halfImageSize }'>
          <q-img :src='token0Logo' :width='imgSize' :height='imgSize' fit='cover' />
        </div>
        <div :style='{ width: halfImageSize, overflow: "hidden", borderTopRightRadius: halfImageSize, borderBottomRightRadius: halfImageSize }'>
          <q-img :src='token1Logo' :width='imgSize' :height='imgSize' :style='{ marginLeft: `-${halfImageSize}` }' fit='cover' />
        </div>
      </div>
    </div>
    <div class='q-ml-md column justify-center' :style='{ width: `calc(100% - ${avatarSize} - 16px)` }'>
      <div class='row text-bold' :style='{fontSize: poolNameFontSize}'>
        <div class='q-mr-sm'>{{ token0Ticker }}</div>
        /
        <div class='q-ml-sm'>{{ token1Ticker }}</div>
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

interface Props {
  token0Application?: ams.Application
  token1Application?: ams.Application
  showRank?: boolean
  avatarSize?: string
  showChips?: boolean
  poolNameFontSize?: string
}
const props = withDefaults(defineProps<Props>(), {
  showRank: true,
  avatarSize: '66px',
  showChips: true,
  poolNameFontSize: '20px'
})
const token0Application = toRef(props, 'token0Application')
const token1Application = toRef(props, 'token1Application')
const showRank = toRef(props, 'showRank')
const avatarSize = toRef(props, 'avatarSize')
const showChips = toRef(props, 'showChips')
const poolNameFontSize = toRef(props, 'poolNameFontSize')

const token0Logo = computed(() => ams.Ams.applicationLogo(token0Application.value || {} as ams.Application) || constants.LINERA_LOGO)
const token1Logo = computed(() => ams.Ams.applicationLogo(token1Application.value || {} as ams.Application) || constants.LINERA_LOGO)
const token0Meme = computed(() => JSON.parse(token0Application.value?.spec || '{}') as meme.Meme)
const token1Meme = computed(() => JSON.parse(token1Application.value?.spec || '{}') as meme.Meme)
const token0Ticker = computed(() => token0Meme.value?.ticker || constants.LINERA_TICKER)
const token1Ticker = computed(() => token1Meme.value?.ticker || constants.LINERA_TICKER)

const imgSize = computed(() => (Number(avatarSize.value.replace('px', '')) - 10) + 'px')
const halfImageSize = computed(() => (Number(avatarSize.value.replace('px', '')) - 10) / 2 + 'px')

</script>
