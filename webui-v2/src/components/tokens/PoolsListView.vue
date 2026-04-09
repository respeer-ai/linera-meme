<template>
  <div>
    <q-table
      :columns='(columns as never)'
      :rows='pools'
      row-key='id'
      separator='none'
    >
      <template #header='props'>
        <q-tr class='text-neutral bg-dark-secondary' :props='props'>
          <q-th class='cursor-pointer text-left'>#</q-th>
          <q-th class='cursor-pointer text-left'>Pool</q-th>
          <q-th class='cursor-pointer'>Fee tier</q-th>
          <q-th class='cursor-pointer'>TVL</q-th>
          <q-th class='cursor-pointer'>Pool APR</q-th>
          <q-th class='cursor-pointer'>1D vol</q-th>
          <q-th class='cursor-pointer'>30D vol</q-th>
          <!-- q-th class='cursor-pointer'>1D chart</q-th -->
          <q-th class='cursor-pointer'>Actions</q-th>
        </q-tr>
      </template>

      <template #body='props'>
        <q-tr :props='props' class='cursor-pointer'>
          <td :props='props' class='text-left'>{{ props.rowIndex + 1 }}</td>
          <td :props='props' class='text-left row items-center'>
            <pool-logo-view
              :token0-application='(ams.Ams.application(props.row.token0) as ams.Application)'
              :token1-application='(ams.Ams.application(props.row.token1) as ams.Application)'
              :show-rank='false'
              avatar-size='36px'
              :show-chips='false'
              pool-name-font-size='14px'
            />
          </td>
          <td :props='props' class='text-center'>{{ constants.PROTOCOL_SWAP_FEE_PERCENT_LABEL }}</td>
          <td :props='props' class='text-center'>
            {{ poolTvl(props.row) }}
          </td>
          <td :props='props' class='text-center'>
            {{ apr(props.row) }}
          </td>
          <td :props='props' class='text-center'>{{ poolOneDayVolume(props.row) }}</td>
          <td :props='props' class='text-center'>{{ poolOneMonthVolume(props.row) }}</td>
          <!-- td :props='props' class='text-center'>0 TLINERA</td -->
          <td :props='props' class='text-center'>
            <div class='narrow-btn'>
              <q-btn dense no-caps rounded flat class='text-secondary' @click='onAddLiquidityClick(props.row)'>
                Add liquidity
              </q-btn>
            </div>
          </td>
        </q-tr>
      </template>

      <template #bottom>
        <div class='full-width row items-center justify-center' style='line-height: 30px;'>
          <q-pagination
            v-model='pagination.page'
            :max='totalPages'
            boundary-links
            size='md'
            color='secondary'
          />
        </div>
      </template>
    </q-table>
  </div>
</template>

<script setup lang='ts'>
import { ams, meme, swap, kline } from 'src/stores/export'
import { computed, onMounted, ref } from 'vue'
import { Pool } from 'src/__generated__/graphql/swap/graphql'
import { constants } from 'src/constant'
import { protocol } from 'src/utils'
import { useRouter } from 'vue-router'
import { buildAddLiquidityRoute } from '../pools/poolFlow'

import PoolLogoView from '../pools/PoolLogoView.vue'

const router = useRouter()

const tokens = computed(() => ams.Ams.applications().map((el) => {
  return {
    ...el,
    meme: JSON.parse(el.spec) as meme.Meme
  }
}) || [])

const pools = computed(() => swap.Swap.pools())

const columns = computed(() => [
  {
    name: 'PoolIndex',
    label: '#',
    align: 'left',
    field: 0
  },
  {
    name: 'Pool',
    label: 'Pool',
    align: 'center',
    field: (row: Pool) => row.token0
  },
  {
    name: 'FeeTier',
    label: 'Fee tier',
    align: 'center',
    field:  '0.15%'
  },
  {
    name: 'TVL',
    label: 'TVL',
    align: 'center',
    field: '1.23%'
  },
  {
    name: 'OneDayChange',
    label: '1 Day',
    align: 'center',
    field: 'US $10.23B'
  },
  {
    name: 'PoolAPR',
    label: 'PoolAPR',
    align: 'center',
    field: '4.23%'
  },
  {
    name: 'OneDayVolume',
    label: '1D vol',
    align: 'center',
    field: '10.23B'
  },
  {
    name: 'ThirtyDayVolume',
    label: '30D vol',
    align: 'center',
    field: '10.23B'
  },
  {
    name: 'Actions',
    label: 'Actions',
    align: 'center',
    field: 'Add liquidity'
  }
])

const pagination = ref({
  page: 1,
  rowsPerPage: 10
})
const totalPages = computed(() => Math.ceil(tokens.value.length / pagination.value.rowsPerPage))

const nativePriceMap = computed(() => protocol.buildNativePriceMap(pools.value))

const formatNativeAmount = (value: number | undefined) => {
  return value === undefined ? '--' : `${value.toFixed(4)} TLINERA`
}

const poolOneDayVolume = (pool: Pool) => {
  const volume = protocol.calculatePoolVolumeInNative(
    kline.Kline.poolStat(pool.poolId, kline.TickerInterval.OneDay),
    nativePriceMap.value,
  )
  return formatNativeAmount(volume)
}

const poolOneMonthVolume = (pool: Pool) => {
  const volume = protocol.calculatePoolVolumeInNative(
    kline.Kline.poolStat(pool.poolId, kline.TickerInterval.OneMonth),
    nativePriceMap.value,
  )
  return formatNativeAmount(volume)
}

const poolTvl = (pool: Pool) => {
  const tvl = protocol.calculatePoolTvlInNative(pool, nativePriceMap.value)
  return formatNativeAmount(tvl)
}

const apr = (pool: Pool) => {
  const tvl = protocol.calculatePoolTvlInNative(pool, nativePriceMap.value)
  const oneDayVolume = protocol.calculatePoolVolumeInNative(
    kline.Kline.poolStat(pool.poolId, kline.TickerInterval.OneDay),
    nativePriceMap.value,
  )
  if (tvl === undefined || oneDayVolume === undefined) return '--'
  return `${protocol.calculatePoolAprFromDailyVolume(oneDayVolume, tvl).toFixed(4)}%`
}

const onAddLiquidityClick = (pool: Pool) => {
  void router.push(buildAddLiquidityRoute(pool))
}

onMounted(async () => {
  await kline.Kline.getPoolStats(kline.TickerInterval.OneDay)
  await kline.Kline.getPoolStats(kline.TickerInterval.OneMonth)
})

</script>

<style scoped lang='sass'>
.q-table
  th
    font-size: 14px
  tbody td
    font-size: 16px

::v-deep(.q-pagination)
  .q-btn
    line-height: 24px
    min-height: 24px

</style>
