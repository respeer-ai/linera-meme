<template>
  <div>
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
import { computed, onMounted } from 'vue'
import { ams, kline, swap } from 'src/stores/export'
import { TickerInterval } from 'src/stores/kline'
import { buildTrendingBulletins } from './trendingData'

import BulletinListView from '../bulletin/BulletinListView.vue'

const applications = computed(() => ams.Ams.applications())
const poolsByToken = computed(() => {
  return new Map(
    swap.Swap.pools()
      .filter((pool) => pool.token1)
      .map((pool) => [
        pool.token0 === 'TLINERA' ? (pool.token1 as string) : pool.token0,
        pool,
      ]),
  )
})
const oneDayTickers = computed(() => {
  const stats = applications.value
    .map((application) => [
      application.applicationId,
      kline.Kline.tokenStat(application.applicationId, TickerInterval.OneDay),
    ] as const)
    .filter((entry): entry is readonly [string, kline.TickerStat] => Boolean(entry[1]))

  return new Map(stats)
})

const topGainerTokens = computed(() => buildTrendingBulletins('gainers', {
  applications: applications.value,
  tickersByToken: oneDayTickers.value,
  poolsByToken: poolsByToken.value,
  applicationLogo: ams.Ams.applicationLogo,
}))
const topVolumeTokens = computed(() => buildTrendingBulletins('volume', {
  applications: applications.value,
  tickersByToken: oneDayTickers.value,
  poolsByToken: poolsByToken.value,
  applicationLogo: ams.Ams.applicationLogo,
}))
const newTokens = computed(() => buildTrendingBulletins('new', {
  applications: applications.value,
  tickersByToken: oneDayTickers.value,
  poolsByToken: poolsByToken.value,
  applicationLogo: ams.Ams.applicationLogo,
}))

onMounted(async () => {
  await kline.Kline.getTickers(TickerInterval.OneDay)
})

</script>
