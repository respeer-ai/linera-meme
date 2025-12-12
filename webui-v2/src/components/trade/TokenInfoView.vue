<template>
  <div>
    <q-img :src='tokenLogo' style='width: 100%; height: 120px;' fit='contain'>
      <div class='fill-parent-width fill-parent-height flex items-end justify-end radius-top-8'>
        <div>
          <div class='font-size-20 text-bold fill-parent-width text-right'>$ {{ tokenTicker }}</div>
          <div class='fill-parent-width text-right text-neutral ellipsis-lines-2'>{{ tokenDescription }}</div>
        </div>
      </div>
    </q-img>
    <div class='row q-mt-sm'>
      <q-space />
      <q-chip class='bg-mining'>Minable</q-chip>
      <q-chip class='bg-virtual'>Virtual LP</q-chip>
      <q-chip class='bg-secondary'>Trending #1</q-chip>
      <q-space />
    </div>
    <div class='q-px-md'>
      <div class='q-mt-md'>
        <token-info-line-view label='Price' value='0.00001245 TLINERA' value-color='light' :value-bold='true' :underline='false' />
        <div class='q-mt-sm'>
          <token-info-line-view label='24H Change' value='+ 12.34 %' value-color='secondary' :value-bold='false' :underline='false' />
        </div>
        <div class='q-mt-sm'>
          <token-info-line-view label='24H Volume' value='123.456 TLINERA' value-color='light' :value-bold='true' :underline='false' />
        </div>
        <div class='q-mt-sm'>
          <token-info-line-view label='Liquidity' value='456.789 TLINERA' value-color='light' :value-bold='true' :underline='false' />
        </div>
        <div class='q-mt-sm'>
          <token-info-line-view label='Mining APY' value='18.78%' value-color='mining' :value-bold='false' :underline='true' />
        </div>
        <div class='q-mt-sm'>
          <token-info-line-view label='Price Impact' value='2.78%' value-color='warning' :value-bold='false' :underline='false' />
        </div>
      </div>
      <div class='q-mt-md'>
        <q-chip class='bg-mining'>X</q-chip>
        <q-chip class='bg-virtual'>Discord</q-chip>
        <q-chip class='bg-secondary'>Telegram</q-chip>
        <q-chip class='bg-secondary'>Github</q-chip>
        <q-chip class='bg-secondary'>Website</q-chip>
      </div>
    </div>
    <div class='q-mt-md radius-bottom-8' style='overflow: hidden;'>
      <youtube :src='videoUrl' :vars='{ autoplay: 1 }' height='200' width='100%' />
      <div class='row q-ma-sm items-center'>
        <q-avatar size='24px'>
          <q-icon name='info' size='24px' />
        </q-avatar>
        <div class='q-ml-sm'>
          <div>MEME Token AMA</div>
          <div class='font-size-12 text-neutral'>1.2K Viewers</div>
        </div>
        <q-space />
        <div class='narrow-btn'>
          <q-btn flat dense rounded class='bg-primary-twenty-five text-primary'>Watch</q-btn>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, toRef } from 'vue'
import { Token } from './Token'
import Youtube from 'vue3-youtube'
import { ams } from 'src/stores/export'
import { constants } from 'src/constant'

import TokenInfoLineView from './TokenInfoLineView.vue'

interface Props {
  token: Token
}
const props = defineProps<Props>()
const token = toRef(props, 'token')

const videoUrl = 'https://www.youtube.com/embed/xIfcHh0bPbk'

const tokenLogo = computed(() => ams.Ams.applicationLogo(token.value as ams.Application) || constants.LINERA_LOGO)
const tokenTicker = computed(() => token.value?.meme?.ticker || constants.LINERA_TICKER)
const tokenDescription = computed(() => token.value?.description || constants.LINERA_DESCRIPTION)
</script>
