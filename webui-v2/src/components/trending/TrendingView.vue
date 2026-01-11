<template>
  <div>
    <div class='row items-center'>
      <section-title-view icon='trending_up' title='Trending Tokens' />
      <q-space />
      <div class='narrow-btn'>
        <q-btn flat dense rounded class='text-primary' @click='onViewAllClick'>View All</q-btn>
      </div>
    </div>
    <div class='q-mt-md row flex flex-wrap' style='justify-content: center; gap: 16px;'>
      <div style='flex: 1 1 0; max-width: calc((100% - 32px) / 3); min-width: 240px;'>
        <bulletin-list-view icon='trending_up' label='Top Gainers' :data='topGainerTokens' />
      </div>
      <div style='flex: 1 1 0; max-width: calc((100% - 32px) / 3); min-width: 240px;'>
        <bulletin-list-view icon='pie_chart' label='Top Volume' :data='topVolumeTokens' />
      </div>
      <div style='flex: 1 1 0; max-width: calc((100% - 32px) / 3); min-width: 240px;'>
        <bulletin-list-view icon='rocket_launch' label='New Tokens' :data='newTokens' />
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { ams, meme, swap } from 'src/stores/export'
import { BulletinItem } from '../bulletin/BulletinItem'
import { constants } from 'src/constant'
import { useRouter } from 'vue-router'

import SectionTitleView from '../common/SectionTitleView.vue'
import BulletinListView from '../bulletin/BulletinListView.vue'

const token2BulletinItem = (application: ams.Application, imageBorderColor: string, valueColor: string, caption: string, captionColor: string) => {
  const meme = JSON.parse(application.spec) as meme.Meme
  const pool = swap.Swap.getPool(application.applicationId, constants.LINERA_NATIVE_ID)
  const price = (Number(application.applicationId === pool?.token0 ? pool?.token0Price : pool?.token1Price) || 0).toFixed(6)

  return {
    image: ams.Ams.applicationLogo(application),
    imageBorderColor,
    label: meme?.ticker,
    subtitle: meme?.name,
    value: price,
    valueColor,
    caption,
    captionColor
  } as BulletinItem
}

const topGainerTokens = computed(() => ams.Ams.applications().map((el) => token2BulletinItem(el, 'primary-twenty-five', 'light', '+ 12.34%', 'secondary')))
const topVolumeTokens = computed(() => ams.Ams.applications().map((el) => token2BulletinItem(el, 'secondary-twenty-five', 'light', '123,456 TLINERA', 'volume')))
const newTokens = computed(() => ams.Ams.applications().map((el) => token2BulletinItem(el, 'neutral-twenty-five', 'light', '~ 2H', 'warning')))

const router = useRouter()

const onViewAllClick = () => {
  void router.push({ path: '/tokens' })
}

</script>
