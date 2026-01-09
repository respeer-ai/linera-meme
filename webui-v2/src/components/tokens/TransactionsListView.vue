<template>
  <div>
    <q-table
      :columns='(columns as never)'
      :rows='transactions'
      row-key='id'
      separator='none'
      @request='onPageRequest'
      :loading='loading'
      :virtual-scroll='true'
      hide-pagination
    >
      <template #header='props'>
        <q-tr class='text-neutral bg-dark-secondary' :props='props'>
          <q-th class='cursor-pointer text-left'>Time</q-th>
          <q-th class='cursor-pointer text-left'>Swap</q-th>
          <q-th class='cursor-pointer'>Value</q-th>
          <q-th class='cursor-pointer'>Amount</q-th>
          <q-th class='cursor-pointer'>Amount</q-th>
          <q-th class='cursor-pointer'>Address</q-th>
        </q-tr>
      </template>

      <template #body='props'>
        <q-tr :props='props' class='cursor-pointer'>
          <td :props='props' class='text-left'>{{ timestamp.timestamp2HumanReadable(props.row.created_at * 1000) }}</td>
          <td :props='props' class='text-left row items-center'>
            <div class='text-neutral q-mr-xs'>Swap</div>
            {{ tokenTicker(buyToken(props.row)) }}
            <q-avatar class='q-mx-sm' size='20px'>
              <q-img :src='tokenLogo(buyToken(props.row))' width='20px' height='20px' />
            </q-avatar>
            <div class='text-neutral q-ml-xs q-mr-sm'>for</div>
            {{ tokenTicker(sellToken(props.row)) }}
            <q-avatar class='q-ml-sm' size='20px'>
              <q-img :src='tokenLogo(sellToken(props.row))' width='20px' height='20px' />
            </q-avatar>
          </td>
          <td :props='props' class='text-center'>0 TLINERA</td>
          <td :props='props' class='text-center'>
            {{ Number(buyAmount(props.row)).toFixed(5) }}
            <q-avatar class='q-ml-xs' size='20px'>
              <q-img :src='tokenLogo(buyToken(props.row))' width='20px' height='20px' />
            </q-avatar>
          </td>
          <td :props='props' class='text-center'>
            {{ Number(sellAmount(props.row)).toFixed(5) }}
            <q-avatar class='q-ml-xs' size='20px'>
              <q-img :src='tokenLogo(sellToken(props.row))' width='20px' height='20px' />
            </q-avatar>
          </td>
          <td :props='props' class='text-center'>{{ shortid.shortId(props.row.from_account, 12, 10) }}</td>
        </q-tr>
      </template>

      <template #bottom>
        <div class='full-width row items-center justify-center' style='line-height: 30px;'>
          <q-pagination
            v-model='pagination.page'
            :max='pagination.rowsNumber'
            :max-pages='6'
            boundary-links
            boundary-numbers
            direction-links
            size='md'
            color='secondary'
          />
        </div>
      </template>
    </q-table>
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted, watch, onBeforeUnmount, ref, onBeforeMount, toRef } from 'vue'
import { ams, meme, swap, transaction, kline } from 'src/stores/export'
import { klineWorker } from 'src/worker'
import { Token } from '../trade/Token'
import { constants } from 'src/constant'
import { shortid, timestamp } from 'src/utils'

interface Props {
  token0?: string
  token1?: string
}
const props = defineProps<Props>()
const token0 = toRef(props, 'token0')
const token1 = toRef(props, 'token1')

const pools = computed(() => swap.Swap.pools())

const tokenTicker = (token: string) => {
  const application = ams.Ams.application(token) as Token
  if (!application) return constants.LINERA_NATIVE_ID
  return (JSON.parse(application?.spec || '{}') as meme.Meme).ticker || constants.LINERA_NATIVE_ID
}

const tokenLogo = (token: string) => {
  const application = ams.Ams.application(token) as Token
  if (!application) return constants.LINERA_LOGO
  return ams.Ams.applicationLogo(application)
}

const transactionPool = (_transaction: transaction.TransactionExt) => {
  return pools.value.find((el) => el.poolId === _transaction.pool_id)
}

const buyToken = (_transaction: transaction.TransactionExt) => {
  const pool = transactionPool(_transaction)
  return _transaction.direction === 'Buy' ? pool?.token1 : pool?.token0
}

const sellToken = (_transaction: transaction.TransactionExt) => {
  const pool = transactionPool(_transaction)
  return _transaction.direction === 'Buy' ? pool?.token0 : pool?.token1
}

const buyAmount = (_transaction: transaction.TransactionExt) => {
  return _transaction.direction === 'Buy' ? _transaction.amount_1_in : _transaction.amount_0_in
}

const sellAmount = (_transaction: transaction.TransactionExt) => {
  return _transaction.direction === 'Sell' ? _transaction.amount_1_out : _transaction.amount_0_out
}

const columns = computed(() => [
  {
    name: 'Time',
    label: 'Time',
    align: 'left',
    field: (row: transaction.TransactionExt) => row.created_at
  },
  {
    name: 'Swap',
    label: 'Swap',
    align: 'center',
    field: (row: transaction.TransactionExt) => row.pool_id
  },
  {
    name: 'Value',
    label: 'Value',
    align: 'center',
    field:  'USD $ 3145.23'
  },
  {
    name: 'Amount',
    label: 'Amount',
    align: 'center',
    field: (row: transaction.TransactionExt) => row.amount_0_in
  },
  {
    name: 'Amount',
    label: 'Amount',
    align: 'center',
    field: (row: transaction.TransactionExt) => row.amount_1_out
  },
  {
    name: 'Address',
    label: 'Address',
    align: 'center',
    field: (row: transaction.TransactionExt) => row.from_account
  }
])

const pagination = ref({
  page: 1,
  rowsPerPage: 10,
  rowsNumber: 10
})

const loading = ref(false)

const selectedToken0 = computed(() => token0.value as string)
const selectedToken1 = computed(() => token1.value as string)
const selectedPool = computed(() => swap.Swap.getPool(token0.value as string, token1.value as string))
const tokenReversed = computed(() => (selectedToken0.value === selectedPool.value?.token1) && selectedToken0.value !== undefined && selectedToken1.value !== undefined)
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000))
const loadInterval = ref(600 * 1000)

const transactions = ref([] as transaction.TransactionExt[])
const latestTransactions = computed(() => kline.Kline.latestTransactions(selectedToken0.value, selectedToken1.value, tokenReversed.value))

const getTransactions = (startAt: number, endAt: number) => {
  if (selectedToken0.value === selectedToken1.value && selectedToken0.value && selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt
  })
}

const loadTransactions = (timestampBegin: number | undefined, timestampEnd: number | undefined, limit: number) => {
  if (selectedToken0.value === selectedToken1.value && selectedToken0.value && selectedToken1.value) return false

  loading.value = true

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.LOAD_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    tokenReversed: tokenReversed.value,
    timestampBegin,
    timestampEnd,
    limit
  } as klineWorker.LoadTransactionsPayload)

  return true
}

const getTransactionsInformation = async () => {
  const info = await kline.Kline.getTransactionsInformation(selectedToken0.value, selectedToken1.value)
  if (!info) return
  // TODO: record timestamp begin and end then we can control data loading
  pagination.value.rowsNumber = info.count
}

const getStoreTransactions = async () => {
  transactions.value = []
  if (loading.value) return

  if (loadTransactions(undefined, undefined, 20)) {
    await getTransactionsInformation()
  }
}

watch(selectedToken0, async () => {
  // await getStoreTransactions()
})

watch(selectedToken1, async () => {
  // await getStoreTransactions()
})

watch(selectedPool, async () => {
  await getStoreTransactions()
})

enum SortReason {
  FETCH = 'Fetch',
  LOAD = 'Load',
  LATEST = 'Latest'
}

type ReasonPayload = { startAt: number, endAt: number }

interface Reason {
  reason: SortReason
  payload: ReasonPayload
}

const MAX_TRANSACTIONS = -1

watch(latestTransactions, () => {
  if (!latestTransactions.value.length) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originTransactions: transactions.value.map((el) => {
      return { ...el }
    }),
    newTransactions: latestTransactions.value.map((el) => {
      return { ...el }
    }),
    tokenReversed: tokenReversed.value,
    keepCount: MAX_TRANSACTIONS,
    reverse: true,
    reason: {
      reason: SortReason.LATEST,
      payload: undefined
    }
  })
})

const onFetchedTransactions = (payload: klineWorker.FetchedTransactionsPayload) => {
  const { token0, token1, startAt } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originTransactions: [],
    newTransactions: payload.transactions.map((el) => {
      return { ...el }
    }),
    tokenReversed: tokenReversed.value,
    keepCount: MAX_TRANSACTIONS,
    reverse: true,
    reason: {
      reason: SortReason.FETCH,
      payload: {
        startAt: startAt - loadInterval.value,
        endAt: startAt - 1
      }
    }
  })
}

const onLoadedTransactions = async (payload: klineWorker.LoadedTransactionsPayload) => {
  const _transactions = payload.transactions || []
  const { token0, token1, timestampBegin, timestampEnd } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) {
    if (loadTransactions(timestampBegin, timestampEnd, 20)) {
      await getTransactionsInformation()
    }
    return
  }

  const startAt = (payload.timestampBegin ?? (_transactions[0]?.created_at || new Date().getTime())) - loadInterval.value
  const endAt = (payload.timestampBegin ?? (_transactions[0]?.created_at || new Date().getTime())) - 1

  const reason = {
    reason: SortReason.LOAD,
    payload: {
      startAt,
      endAt
    }
  }

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originTransactions: [],
    newTransactions: _transactions.map((el) => {
      return { ...el }
    }),
    tokenReversed: tokenReversed.value,
    keepCount: MAX_TRANSACTIONS,
    reverse: true,
    reason
  })
}

const onSortedTransactions = (payload: klineWorker.SortedTransactionsPayload) => {
  const _reason = payload.reason as Reason
  const { token0, token1 } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  if (payload.transactions.length === 0) {
    const startAt = _reason.payload.startAt
    const endAt = _reason.payload.endAt

    if (endAt < poolCreatedAt.value) {
      loading.value = false
      return
    }
    if (startAt > new Date().getTime()) {
      loading.value = false
      return
    }

    return getTransactions(_reason.payload.startAt, _reason.payload.endAt)
  }

  transactions.value = payload.transactions.slice(0, 10)
  loading.value = false
}

const onPageRequest = (requestProp: { pagination: { page: number; rowsPerPage: number }}) => {
  if (loading.value) return

  const startAt = (transactions.value[0]?.created_at || new Date().getTime()) - 1
  const endAt = (transactions.value[0]?.created_at || new Date().getTime()) - loadInterval.value

  loadTransactions(startAt, endAt, 20)
  pagination.value.page = requestProp.pagination.page
}

watch(() => pagination.value.page, () => {
  onPageRequest({ pagination: pagination.value })
})

onBeforeMount(() => {
  loading.value = false
})

onMounted(async () => {
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_TRANSACTIONS, onFetchedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.LOADED_TRANSACTIONS, onLoadedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.SORTED_TRANSACTIONS, onSortedTransactions as klineWorker.ListenerFunc)

  ams.Ams.getApplications()
  swap.Swap.getPools()

  await getStoreTransactions()
})

onBeforeUnmount(() => {
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.FETCHED_TRANSACTIONS, onFetchedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.LOADED_TRANSACTIONS, onLoadedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.SORTED_TRANSACTIONS, onSortedTransactions as klineWorker.ListenerFunc)
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
