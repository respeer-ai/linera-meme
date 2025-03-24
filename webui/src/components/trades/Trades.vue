<template>
  <q-table
    flat
    :columns='(columns as never)'
    :rows='tradesStore.Transactions'
    :rows-per-page-options='[10]'
  />
</template>

<script setup lang='ts'>
import { watch, onMounted, computed, onBeforeUnmount } from 'vue'
import { useSwapStore } from 'src/mystore/swap'
import { Transaction, useTradesStore } from 'src/mystore/trades'
import { date } from 'quasar'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const swapStore = useSwapStore()
const tradesStore = useTradesStore()
let intervalID: number

watch(() => swapStore.SelectedTokenPair, (selected) => {
  if (!selected) {
    tradesStore.SelectedPoolID = null
  } else {
    tradesStore.SelectedPoolID = selected.PoolID
  }

  initKPointsStore()
})

const initKPointsStore = () => {
  tradesStore.OriginalTxID = 0
  tradesStore.Transactions = []
  tradesStore.ResetTableViewLock = 0
  tradesStore.refreshHistoryTransactions()
}

onMounted(() => {
  if (tradesStore.NeedInitTxTable) {
    tradesStore.refreshHistoryTransactions()
    tradesStore.NeedInitTxTable = false
  }

  intervalID = window.setInterval(() => {
    tradesStore.refreshNewTransactions()
    if (tradesStore.ResetTableViewLock + 60000 < new Date().getTime()) {
      tradesStore.ResetTableViewLock = new Date().getTime()
    }
  }, 3000)
})

onBeforeUnmount(() => {
  window.clearInterval(intervalID)
})

const columns = computed(() => [
  {
    name: 'TransactionType',
    label: t('MSG_TRANSACTION_TYPE'),
    align: 'left',
    field: 'TransactionType'
  },
  {
    name: 'Address',
    label: t('MSG_ADDRESS'),
    align: 'center',
    field: 'Owner'
  },
  {
    name: 'Action',
    label: t('MSG_ACTION'),
    align: 'center',
    field: (row: Transaction) => row.AmountZeroIn > 0 ? 'Deposit' : 'Withdraw'
  },
  {
    name: 'Amount',
    label: t('MSG_AMOUNT'),
    align: 'center',
    field: (row: Transaction) => row.AmountZeroOut > 0 ? row.AmountZeroOut : row.AmountOneOut
  },
  {
    name: 'Date',
    label: t('MSG_DATE'),
    align: 'center',
    field: (row: Transaction) => date.formatDate(row.Timestamp * 1000, 'YYYY/MM/DD HH:mm:ss')
  }
])

</script>

<style scoped lang='sass'>
:deep(td)
  height: 36px !important
</style>
