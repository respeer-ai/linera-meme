<template>
  <div>
    <q-table
      :columns='(columns as never)'
      :rows='tokens'
      row-key='id'
      separator='none'
    >
      <template #header='props'>
        <q-tr class='text-neutral bg-dark-secondary' :props='props'>
          <q-th class='cursor-pointer text-left'>#</q-th>
          <q-th class='cursor-pointer text-left'>Token name</q-th>
          <q-th class='cursor-pointer'>Price</q-th>
          <q-th class='cursor-pointer'>1 Hour</q-th>
          <q-th class='cursor-pointer'>1 Day</q-th>
          <q-th class='cursor-pointer'>FDV</q-th>
          <q-th class='cursor-pointer'>Volume</q-th>
          <!-- q-th class='cursor-pointer'>1D chart</q-th -->
          <q-th class='cursor-pointer'>Actions</q-th>
        </q-tr>
      </template>

      <template #body='props'>
        <q-tr :props='props' class='cursor-pointer'>
          <td :props='props' class='text-left'>{{ props.rowIndex + 1 }}</td>
          <td :props='props' class='text-left row items-center'>
            <q-avatar size='24px'>
              <q-img :src='ams.Ams.applicationLogo(props.row)' />
            </q-avatar>
            <div class='q-ml-sm'>
              {{ props.row.applicationName }}
            </div>
            <div class='q-ml-sm text-neutral'>
              {{ props.row.meme.ticker }}
            </div>
          </td>
          <td :props='props' class='text-center'>{{ tokenPrice(props.row.applicationId) }} TLINERA</td>
          <td :props='props' class='text-center'>
            <q-icon
              v-if='shouldDisplayDirectionIcon(oneHourPriceDirection(props.row.applicationId))'
              :name='directionIcon(oneHourPriceDirection(props.row.applicationId))'
              :color='directionIconColor(oneHourPriceDirection(props.row.applicationId))'
              size='24px'
            />
            {{ oneHourPriceChange(props.row.applicationId) }}%
          </td>
          <td :props='props' class='text-center'>
            <q-icon
              v-if='shouldDisplayDirectionIcon(oneDayPriceDirection(props.row.applicationId))'
              :name='directionIcon(oneDayPriceDirection(props.row.applicationId))'
              :color='directionIconColor(oneDayPriceDirection(props.row.applicationId))'
              size='24px' 
            />
            {{ oneDayPriceChange(props.row.applicationId) }}%
          </td>
          <td :props='props' class='text-center'>{{ tokenFDV(props.row) }} TLINERA</td>
          <td :props='props' class='text-center'>{{ tokenVolume(props.row.applicationId) }} TLINERA</td>
          <!-- td :props='props' class='text-center'>0 TLINERA</td -->
          <td :props='props' class='text-center'>
            <div class='narrow-btn'>
              <q-btn dense no-caps rounded flat class='text-secondary' disable>
                Join mining
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
import { ams, kline, meme, swap } from 'src/stores/export'
import { computed, onMounted, ref, toRef, watch } from 'vue'
import { Token } from '../trade/Token'

interface Props {
  volumeInterval: kline.TickerInterval
}
const props = defineProps<Props>()
const volumeInterval = toRef(props, 'volumeInterval')

const tokens = computed(() => ams.Ams.applications().map((el) => {
  return {
    ...el,
    meme: JSON.parse(el.spec) as meme.Meme
  }
}) || [])

const columns = computed(() => [
  {
    name: 'TokenIndex',
    label: '#',
    align: 'left',
    field: 0
  },
  {
    name: 'TokenName',
    label: 'Token name',
    align: 'center',
    field: (row: Token) => row.applicationName
  },
  {
    name: 'Price',
    label: 'Price',
    align: 'center',
    field:  0
  },
  {
    name: 'OneHourChange',
    label: '1 Hour',
    align: 'center',
    field: '1.23%'
  },
  {
    name: 'OneDayChange',
    label: '1 Day',
    align: 'center',
    field: '2.22%'
  },
  {
    name: 'FDV',
    label: 'FCV',
    align: 'center',
    field: '10.23B'
  },
  {
    name: 'Volume',
    label: 'Volume',
    align: 'center',
    field: '10.23B'
  },
  {
    name: 'OneDayChart',
    label: '1D chart',
    align: 'center',
    field: '10.23B'
  },
  {
    name: 'Actions',
    label: 'Actions',
    align: 'center',
    field: 'Join mining'
  }
])

const pagination = ref({
  page: 1,
  rowsPerPage: 10
})
const totalPages = computed(() => Math.ceil(tokens.value.length / pagination.value.rowsPerPage))

const tokenPrice = (tokenId: string) => {
  return swap.Swap.tokenPrice(tokenId)
}

const tokenFDV = (token: Token) => {
  const price = Number(tokenPrice(token.applicationId))
  const totalSupply = Number(token.meme.totalSupply)
  return (price * totalSupply).toFixed(4)
}

const tokenVolume = (token: string) => {
  return Number(kline.Kline.tokenStat(token, volumeInterval.value)?.volume)?.toFixed(4) || 0
}

const oneHourPriceChange = (token: string) => {
  const stat = kline.Kline.tokenStat(token, kline.TickerInterval.OneHour)
  if (!stat) return 0
  return (((Number(stat.price_now) - Number(stat.price_start)) / Number(stat.price_start)) * 100).toFixed(4)
}

enum PriceDirection {
  UP = 'Up',
  DOWN = 'Down',
  SAME = 'Same'
}

const oneHourPriceDirection = (token: string) => {
  const stat = kline.Kline.tokenStat(token, kline.TickerInterval.OneHour)
  if (!stat) return PriceDirection.SAME
  return Number(stat.price_now) > Number(stat.price_start) ? PriceDirection.UP : Number(stat.price_now) < Number(stat.price_start) ? PriceDirection.DOWN : PriceDirection.SAME
}

const oneDayPriceDirection = (token: string) => {
  const stat = kline.Kline.tokenStat(token, kline.TickerInterval.OneDay)
  if (!stat) return PriceDirection.SAME
  return Number(stat.price_now) > Number(stat.price_start) ? PriceDirection.UP : Number(stat.price_now) < Number(stat.price_start) ? PriceDirection.DOWN : PriceDirection.SAME
}

const shouldDisplayDirectionIcon = (direction: PriceDirection) => {
  return PriceDirection.SAME === direction ? false : true
}

const directionIcon = (direction: PriceDirection) => {
  return direction ===  PriceDirection.UP ? 'arrow_drop_up' : direction ===  PriceDirection.DOWN ? 'arrow_drop_down' : ''
}

const directionIconColor = (direction: PriceDirection) => {
  return direction ===  PriceDirection.UP ? 'green-4' : direction ===  PriceDirection.DOWN ? 'red-4' : 'blue-4'
}

const oneDayPriceChange = (token: string) => {
  const stat = kline.Kline.tokenStat(token, kline.TickerInterval.OneDay)
  if (!stat) return 0
  return (((Number(stat.price_now) - Number(stat.price_start)) / Number(stat.price_start)) * 100).toFixed(4)
}

watch(volumeInterval, async () => {
  await kline.Kline.getTickers(volumeInterval.value)
})

onMounted(async () => {
  await kline.Kline.getTickers(volumeInterval.value)
  await kline.Kline.getTickers(kline.TickerInterval.OneHour)
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
