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
const tokenReversed = computed(() => selectedToken0.value === selectedPool.value?.token1)

const transactions = ref([] as transaction.TransactionExt[])
const latestTransactions = computed(() => _kline._latestTransactions(selectedToken0.value, selectedToken1.value, tokenReversed.value))

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
    tokenReversed: tokenReversed.value,
    offset,
    limit
  })
}

const getStoreTransactions = () => {
  transactions.value = []
  loadTransactions(0, 100)
}

watch(selectedToken0, () => {
  getStoreTransactions()
})

watch(selectedToken1, () => {
  getStoreTransactions()
})

watch(selectedPool, () => {
  getStoreTransactions()
})

enum SortReason {
  FETCH = 'Fetch',
  LOAD = 'Load',
  LATEST = 'Latest'
}

type ReasonPayload = { endAt: number } | { offset: number, limit: number }

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
  const { token0, token1 } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originTransactions: transactions.value.map((el) => {
      return { ...el }
    }),
    newTransactions: payload.transactions.map((el) => {
      return { ...el }
    }),
    tokenReversed: tokenReversed.value,
    keepCount: MAX_TRANSACTIONS,
    reverse: true,
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
  const { token0, token1 } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  const reason = {
    reason: _transactions.length ? SortReason.LOAD : SortReason.FETCH,
    payload: _transactions.length ? {
      offset: payload.offset + payload.limit,
      limit: payload.limit
    } : {
      endAt: Math.floor(Math.max(...transactions.value.map((el) => Date.parse(el.created_at) / 1000), selectedPool.value?.createdAt / 1000000))
    }
  }

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originTransactions: transactions.value.map((el) => {
      return { ...el }
    }),
    newTransactions: _transactions.map((el) => {
      return { ...el }
    }),
    tokenReversed: tokenReversed.value,
    keepCount: MAX_TRANSACTIONS,
    reverse: true,
    reason
  })
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
  const { token0, token1 } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  let retry = false
  transactions.value.forEach((el) => {
    retry ||= !payload.transactions.map((el) => el.transaction_id).includes(el.transaction_id)
  })
  // If we're not in sorted result, retry sort
  if (retry) {
    klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_TRANSACTIONS, {
      token0: selectedToken0.value,
      token1: selectedToken1.value,
      originTransactions: transactions.value.map((el) => {
        return { ...el }
      }),
      newTransactions: payload.transactions,
      tokenReversed: tokenReversed.value,
      keepCount: MAX_TRANSACTIONS,
      reverse: true,
      reason: payload.reason
    })
    return
  }

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
