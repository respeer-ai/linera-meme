<template>
  <q-table
    flat
    :columns='(columns as never)'
    :rows='transactions'
    :rows-per-page-options='[10]'
  />
</template>

<script setup lang='ts'>
import { computed, onMounted, watch, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { swap, transaction, kline } from 'src/localstore'
import { shortid } from 'src/utils'
import { klineWorker } from 'src/worker'

const { t } = useI18n({ useScope: 'global' })

const columns = computed(() => [
  {
    name: 'TransactionId',
    label: t('MSG_TRANSACTION_ID'),
    align: 'left',
    field: (row: transaction.TransactionExt) => row.transaction_id
  },
  {
    name: 'Address',
    label: t('MSG_ADDRESS'),
    align: 'center',
    field: (row: transaction.TransactionExt) => shortid.shortId(row.from_account, 20, 16)
  },
  {
    name: 'Direction',
    label: t('MSG_DIRECTION'),
    align: 'center',
    field: (row: transaction.TransactionExt) => row.direction
  },
  {
    name: 'Price',
    label: t('MSG_PRICE'),
    align: 'center',
    field: (row: transaction.TransactionExt) => row.price
  },
  {
    name: 'Volume',
    label: t('MSG_VOLUME'),
    align: 'center',
    field: (row: transaction.TransactionExt) => (row.direction === 'Deposit' || row.direction === 'Burn') ? row.liquidity : row.volume
  },
  {
    name: 'Date',
    label: t('MSG_DATE'),
    align: 'center',
    field: (row: transaction.TransactionExt) => row.created_at
  }
])

const _swap = swap.useSwapStore()
const _kline = kline.useKlineStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)

const transactions = ref([] as transaction.TransactionExt[])
const latestTransactions = computed(() => _kline._latestTransactions(selectedToken0.value, selectedToken1.value))

const getTransactions = (startAt: number) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  const endAt = startAt + 3600

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt
  })
}

const loadTransactions = (offset: number, limit: number) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.LOAD_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    offset,
    limit
  })
}

const getPoolTransactions = () => {
  if (selectedPool.value?.createdAt) {
    getTransactions(Math.floor(selectedPool.value?.createdAt / 1000000))
  }
}

const getStoreTransactions = () => {
  loadTransactions(0, 100)
}

watch(selectedToken0, () => {
  getPoolTransactions()
})

watch(selectedToken1, () => {
  getPoolTransactions()
})

watch(selectedPool, () => {
  getPoolTransactions()
})

const updateTransactions = (_transactions: transaction.TransactionExt[], append: boolean) => {
  append ? transactions.value.push(..._transactions) : transactions.value = _transactions
}

watch(latestTransactions, () => {
  updateTransactions(latestTransactions.value, true)
})

const MAX_TRANSACTIONS = -1

enum SortReason {
  FETCH = 'Fetch',
  LOAD = 'Load'
}

type ReasonPayload = { endAt: number } | { offset: number, limit: number }

interface Reason {
  reason: SortReason
  payload: ReasonPayload
}

const onFetchedTransactions = (payload: klineWorker.FetchedTransactionsPayload) => {
  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    originTransactions: transactions.value.map((el) => {
      return { ...el }
    }),
    newTransactions: payload.transactions.map((el) => {
      return { ...el }
    }),
    keepCount: MAX_TRANSACTIONS,
    reverse: false,
    reason: {
      reason: SortReason.FETCH,
      payload: {
        endAt: payload.endAt
      }
    }
  })
}

const onLoadedTransactions = (payload: klineWorker.LoadedTransactionsPayload) => {
  const _transactions = payload.transactions

  const reason = {
    reason: _transactions.length ? SortReason.LOAD : SortReason.FETCH,
    payload: _transactions.length ? {
      offset: payload.offset + payload.limit,
      limit: payload.limit
    } : {
      endAt: Math.floor(Math.max(...transactions.value.map((el) => Date.parse(el.created_at) / 1000)) || selectedPool.value?.createdAt / 1000000)
    }
  }

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    originTransactions: transactions.value.map((el) => {
      return { ...el }
    }),
    newTransactions: payload.transactions.map((el) => {
      return { ...el }
    }),
    keepCount: MAX_TRANSACTIONS,
    reverse: true,
    reason
  })

  if (_transactions.length) loadTransactions(payload.offset + payload.limit, payload.limit)
  else getPoolTransactions()
}

const onFetchSorted = (payload: ReasonPayload) => {
  const { endAt } = payload as { endAt: number }

  if (endAt > Math.floor(Date.now() / 1000)) {
    return
  }

  setTimeout(() => {
    getTransactions(endAt)
  }, 100)
}

const onLoadSorted = (payload: ReasonPayload) => {
  const { offset, limit } = payload as { offset: number, limit: number }

  loadTransactions(offset, limit)
}

const onSortedTransactions = (payload: klineWorker.SortedTransactionsPayload) => {
  const _reason = payload.reason as Reason
  transactions.value = payload.transactions

  switch (_reason.reason) {
    case SortReason.FETCH:
      return onFetchSorted(_reason.payload)
    case SortReason.LOAD:
      return onLoadSorted(_reason.payload)
  }
}

onMounted(() => {
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_TRANSACTIONS, onFetchedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.LOADED_TRANSACTIONS, onLoadedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.SORTED_TRANSACTIONS, onSortedTransactions as klineWorker.ListenerFunc)
  getStoreTransactions()
})

onBeforeUnmount(() => {
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.FETCHED_TRANSACTIONS, onFetchedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.LOADED_TRANSACTIONS, onLoadedTransactions as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.SORTED_TRANSACTIONS, onSortedTransactions as klineWorker.ListenerFunc)
})

</script>

<style scoped lang='sass'>
:deep(td)
  height: 36px !important
</style>
