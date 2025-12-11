<template>
  <div class='row'>
    <div class='row'>
      <div class='bg-primary-twenty-five border-primary-50 row q-pa-xs' style='border-radius: 32px; width: 66px; height: 66px;'>
        <div style='width: 28px; overflow: hidden; border-radius: 28px 0 0 28px;'>
          <q-img :src='token0Logo' width='56px' height='56px' fit='cover' />
        </div>
        <div style='width: 28px; overflow: hidden;; border-radius: 0 28px 28px 0;'>
          <q-img :src='token1Logo' width='56px' height='56px' style='margin-left: -28px;' fit='cover' />
        </div>
      </div>
    </div>
    <div class='q-ml-md' style='width: calc(100% - 66px - 16px);'>
      <div class='row font-size-20 text-bold'>
        <div class='q-mr-sm'>{{ token0Ticker }}</div>
        /
        <div class='q-ml-sm'>{{ token1Ticker }}</div>
      </div>
      <div class='row q-mt-xs' style='margin-left: -4px;'>
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
}
const props = withDefaults(defineProps<Props>(), {
  showRank: true
})
const token0Application = toRef(props, 'token0Application')
const token1Application = toRef(props, 'token1Application')
const showRank = toRef(props, 'showRank')
const token0Logo = computed(() => ams.applicationLogo(token0Application.value || {} as ams.Application) || constants.LINERA_LOGO)
const token1Logo = computed(() => ams.applicationLogo(token1Application.value || {} as ams.Application) || constants.LINERA_LOGO)
const token0Meme = computed(() => JSON.parse(token0Application.value?.spec || '{}') as meme.Meme)
const token1Meme = computed(() => JSON.parse(token1Application.value?.spec || '{}') as meme.Meme)
const token0Ticker = computed(() => token0Meme.value?.ticker || constants.LINERA_TICKER)
const token1Ticker = computed(() => token1Meme.value?.ticker || constants.LINERA_TICKER)

</script>
