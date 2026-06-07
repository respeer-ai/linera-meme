<template>
  <div>
    <q-table
      :columns='(columns as never)'
      :rows='transactions'
      row-key='transaction_id'
      separator='none'
      :loading='loading'
      :virtual-scroll='true'
      hide-pagination
      :rows-per-page-options="[pagination.rowsPerPage]"
      class='transactions-table'
    >
      <template #header='props'>
        <q-tr class='text-neutral bg-dark-secondary' :props='props'>
          <q-th class='text-left'>{{ t('transactions.columns.time') }}</q-th>
          <q-th class='text-left'>{{ t('transactions.columns.swap') }}</q-th>
          <q-th>{{ t('transactions.columns.value') }}</q-th>
          <q-th>{{ t('transactions.columns.bought') }}</q-th>
          <q-th>{{ t('transactions.columns.sold') }}</q-th>
          <q-th>{{ t('transactions.columns.address') }}</q-th>
        </q-tr>
      </template>

      <template #body='props'>
        <q-tr :props='props' class='cursor-pointer'>
          <td :props='props' class='text-left'>{{ timestamp.timestamp2HumanReadable(props.row.created_at) }}</td>
          <td :props='props' class='text-left'>
            <div class='row items-center no-wrap transaction-swap-cell'>
              <div class='text-neutral q-mr-xs'>{{ t('transactions.action.swap') }}</div>
              <span>{{ tokenTicker(buyToken(props.row)) }}</span>
              <q-avatar class='q-mx-sm' size='20px'>
                <q-img :src='tokenLogo(buyToken(props.row))' width='20px' height='20px' />
              </q-avatar>
              <div class='text-neutral q-ml-xs q-mr-sm'>{{ t('transactions.action.for') }}</div>
              <span>{{ tokenTicker(sellToken(props.row)) }}</span>
              <q-avatar class='q-ml-sm' size='20px'>
                <q-img :src='tokenLogo(sellToken(props.row))' width='20px' height='20px' />
              </q-avatar>
            </div>
          </td>
          <td :props='props' class='text-center'>{{ transactionValue(props.row) }}</td>
          <td :props='props' class='text-center'>
            {{ formatTokenAmount(buyAmount(props.row)) }}
            <q-avatar class='q-ml-xs' size='20px'>
              <q-img :src='tokenLogo(buyToken(props.row))' width='20px' height='20px' />
            </q-avatar>
          </td>
          <td :props='props' class='text-center'>
            {{ formatTokenAmount(sellAmount(props.row)) }}
            <q-avatar class='q-ml-xs' size='20px'>
              <q-img :src='tokenLogo(sellToken(props.row))' width='20px' height='20px' />
            </q-avatar>
          </td>
          <td :props='props' class='text-center'>{{ formatAddress(props.row.from_account) }}</td>
        </q-tr>
      </template>

      <template #bottom>
        <div v-if='showPagination' class='full-width row items-center justify-center' style='line-height: 30px;'>
          <q-pagination
            v-model='pagination.page'
            :max='totalPages'
            :max-pages='6'
            boundary-links
            boundary-numbers
            direction-links
            size='md'
            color='secondary'
          />
        </div>
      </template>

      <template #no-data>
        <div class='transactions-empty full-width column items-center justify-center q-pa-lg'>
          <div class='text-body1'>{{ t('transactions.empty.title') }}</div>
          <div class='text-caption text-neutral q-mt-xs'>{{ t('transactions.empty.caption') }}</div>
        </div>
      </template>
    </q-table>
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted, watch, onBeforeUnmount, ref, onBeforeMount, toRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { ams, meme, swap, transaction, kline } from 'src/stores/export'
import { klineWorker } from 'src/worker'
import { Token } from '../trade/Token'
import { constants } from 'src/constant'
import { protocol, shortid, timestamp } from 'src/utils'
import { findPoolByIdentity } from 'src/stores/swap/poolIdentity'

interface Props {
  token0?: string
  token1?: string
}
const props = defineProps<Props>()
const token0 = toRef(props, 'token0')
const token1 = toRef(props, 'token1')
const { t } = useI18n()

const pools = computed(() => swap.Swap.pools())
const nativePriceMap = computed(() => protocol.buildNativePriceMap(pools.value))

const tokenTicker = (token: string | undefined) => {
  if (!token) return '--'
  const application = ams.Ams.application(token) as Token
  if (!application) return constants.LINERA_NATIVE_ID
  return (JSON.parse(application?.spec || '{}') as meme.Meme).ticker || constants.LINERA_NATIVE_ID
}

const tokenLogo = (token: string | undefined) => {
  if (!token) return constants.LINERA_LOGO
  const application = ams.Ams.application(token) as Token
  if (!application) return constants.LINERA_LOGO
  return ams.Ams.applicationLogo(application)
}

const transactionPool = (_transaction: transaction.TransactionExt) => {
  return findPoolByIdentity(pools.value, _transaction.pool_id, _transaction.pool_application)
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
  return _transaction.direction === 'Buy' ? _transaction.amount_0_out : _transaction.amount_1_out
}

const sellAmount = (_transaction: transaction.TransactionExt) => {
  return _transaction.direction === 'Buy' ? _transaction.amount_1_in : _transaction.amount_0_in
}

const formatTokenAmount = (value: unknown) => {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '--'
  return amount.toFixed(5)
}

const formatAddress = (address: string | undefined) => {
  if (!address) return '--'
  return shortid.shortId(address, 12, 10)
}

const transactionValue = (_transaction: transaction.TransactionExt) => {
  const value = protocol.calculateTransactionValueInNative(
    _transaction,
    transactionPool(_transaction),
    nativePriceMap.value,
  )
  return value === undefined ? '--' : `${value.toFixed(4)} TLINERA`
}

const columns = computed(() => [
  {
    name: 'Time',
    label: t('transactions.columns.time'),
    align: 'left',
    field: (row: transaction.TransactionExt) => row.created_at
  },
  {
    name: 'Swap',
    label: t('transactions.columns.swap'),
    align: 'center',
    field: (row: transaction.TransactionExt) => row.pool_id
  },
  {
    name: 'Value',
    label: t('transactions.columns.value'),
    align: 'center',
    field:  'USD $ 3145.23'
  },
  {
    name: 'Amount',
    label: t('transactions.columns.bought'),
    align: 'center',
    field: (row: transaction.TransactionExt) => row.amount_0_in
  },
  {
    name: 'Amount',
    label: t('transactions.columns.sold'),
    align: 'center',
    field: (row: transaction.TransactionExt) => row.amount_1_out
  },
  {
    name: 'Address',
    label: t('transactions.columns.address'),
    align: 'center',
    field: (row: transaction.TransactionExt) => row.from_account
  }
])

const pagination = ref({
  page: 1,
  rowsPerPage: 20,
  rowsNumber: 0
})
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.value.rowsNumber / pagination.value.rowsPerPage)))
const showPagination = computed(() => pagination.value.rowsNumber > pagination.value.rowsPerPage)

const loading = ref(false)

const selectedToken0 = computed(() => token0.value as string)
const selectedToken1 = computed(() => token1.value as string)
const selectedPool = computed(() => swap.Swap.getPool(token0.value as string, token1.value as string))
const tokenReversed = computed(() => (selectedToken0.value === selectedPool.value?.token1) && selectedToken0.value !== undefined && selectedToken1.value !== undefined)
const poolCreatedAt = computed(() => selectedPool.value?.createdAt ?? 0)
const globalTransactionsEndAt = 9999999999999
const pageCursors = ref(new Map<number, { timestampBegin?: number; timestampEnd?: number }>())
const activeRequestId = ref(0)
const mounted = ref(false)

const transactions = ref([] as transaction.TransactionExt[])
const pushedTransactions = computed(() =>
  kline.Kline.pushedTransactions(selectedToken0.value, selectedToken1.value, tokenReversed.value),
)

const getTransactions = (startAt: number, endAt: number) => {
  if (selectedToken0.value === selectedToken1.value && selectedToken0.value && selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt,
    limit: pagination.value.rowsPerPage,
    requestId: activeRequestId.value
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
    limit,
    requestId: activeRequestId.value
  } as klineWorker.LoadTransactionsPayload)

  return true
}

const getTransactionsInformation = async () => {
  const info = await kline.Kline.getTransactionsInformation(selectedToken0.value, selectedToken1.value)
  pagination.value.rowsNumber = info?.count ?? 0
}

const getStoreTransactions = async () => {
  activeRequestId.value += 1
  transactions.value = []
  pageCursors.value = new Map()
  pagination.value = {
    ...pagination.value,
    page: 1,
    rowsNumber: 0
  }
  loading.value = false

  loadTransactions(undefined, undefined, pagination.value.rowsPerPage)
  void getTransactionsInformation()
}

watch([selectedToken0, selectedToken1], async () => {
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

watch(pushedTransactions, () => {
  if (!mounted.value) return
  if (!pushedTransactions.value.length) return
  if (pagination.value.page !== 1) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originTransactions: transactions.value.map((el) => {
      return { ...el }
    }),
    newTransactions: pushedTransactions.value.map((el) => {
      return { ...el }
    }),
    tokenReversed: tokenReversed.value,
    keepCount: pagination.value.rowsPerPage,
    reverse: true,
    reason: {
      reason: SortReason.LATEST,
      payload: undefined
    }
  })
})

const onFetchedTransactions = (payload: klineWorker.FetchedTransactionsPayload) => {
  const { token0, token1, startAt, endAt, requestId } = payload

  if (!mounted.value || requestId !== activeRequestId.value) return
  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originTransactions: [],
    newTransactions: payload.transactions.map((el) => {
      return { ...el }
    }),
    tokenReversed: tokenReversed.value,
    keepCount: pagination.value.rowsPerPage,
    reverse: true,
    reason: {
      reason: SortReason.FETCH,
      payload: {
        startAt,
        endAt
      }
    }
  })
}

const onLoadedTransactions = async (payload: klineWorker.LoadedTransactionsPayload) => {
  const _transactions = payload.transactions || []
  const { token0, token1, timestampBegin, timestampEnd, requestId } = payload

  if (!mounted.value || requestId !== activeRequestId.value) return
  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) {
    if (loadTransactions(timestampBegin, timestampEnd, pagination.value.rowsPerPage)) {
      await getTransactionsInformation()
    }
    return
  }

  const startAt = payload.timestampBegin ?? 0
  const endAt = payload.timestampEnd ?? globalTransactionsEndAt

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
    keepCount: pagination.value.rowsPerPage,
    reverse: true,
    reason
  })
}

const onSortedTransactions = (payload: klineWorker.SortedTransactionsPayload) => {
  const _reason = payload.reason as Reason
  const { token0, token1 } = payload

  if (!mounted.value) return
  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  if (payload.transactions.length === 0) {
    if (_reason.reason === SortReason.LOAD) {
      return getTransactions(_reason.payload.startAt, _reason.payload.endAt)
    }
    if (_reason.reason === SortReason.FETCH) {
      transactions.value = []
      loading.value = false
      return
    }

    return getTransactions(_reason.payload.startAt, _reason.payload.endAt)
  }

  transactions.value = payload.transactions.slice(0, pagination.value.rowsPerPage)
  const oldest = transactions.value[transactions.value.length - 1]
  if (oldest) {
    pageCursors.value.set(pagination.value.page + 1, {
      timestampEnd: oldest.created_at - 1
    })
  }
  loading.value = false
}

const onPageRequest = (requestProp: { pagination: { page: number; rowsPerPage: number }}) => {
  if (loading.value) return

  const nextPage = requestProp.pagination.page
  const cursor = pageCursors.value.get(nextPage)
  const anchor = cursor?.timestampEnd ?? (transactions.value[transactions.value.length - 1]?.created_at || new Date().getTime())
  const startAt = Math.max(poolCreatedAt.value || 0, 0)
  const endAt = anchor

  if (loadTransactions(startAt, endAt, pagination.value.rowsPerPage)) {
    pagination.value.page = nextPage
  }
}

watch(() => pagination.value.page, () => {
  if (!mounted.value) return
  onPageRequest({ pagination: pagination.value })
})

onBeforeMount(() => {
  loading.value = false
})

onMounted(async () => {
  mounted.value = true
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_TRANSACTIONS, onFetchedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.LOADED_TRANSACTIONS, onLoadedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.SORTED_TRANSACTIONS, onSortedTransactions as klineWorker.ListenerFunc)

  ams.Ams.getApplications()
  swap.Swap.getPools()

  await getStoreTransactions()
})

onBeforeUnmount(() => {
  mounted.value = false
  activeRequestId.value += 1
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

.transactions-empty
  min-height: 160px

.transaction-swap-cell
  min-width: 220px

::v-deep(.q-pagination)
  .q-btn
    line-height: 24px
    min-height: 24px

</style>
