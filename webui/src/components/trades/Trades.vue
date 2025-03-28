<template>
  <q-table
    flat
    :columns='(columns as never)'
    :rows='transactions'
    :rows-per-page-options='[10]'
  />
</template>

<script setup lang='ts'>
import { computed, onMounted, watch } from 'vue'
import { date } from 'quasar'
import { useI18n } from 'vue-i18n'
import { pool, swap, transaction } from 'src/localstore'
import { shortid } from 'src/utils'

const { t } = useI18n({ useScope: 'global' })

const columns = computed(() => [
{
    name: 'TransactionId',
    label: t('MSG_TRANSACTION_ID'),
    align: 'left',
    field: (row: transaction.Transaction) => row.transactionId
  },
  {
    name: 'TransactionType',
    label: t('MSG_TRANSACTION_TYPE'),
    align: 'left',
    field: (row: transaction.Transaction) => row.transactionType
  },
  {
    name: 'Address',
    label: t('MSG_ADDRESS'),
    align: 'center',
    field: (row: transaction.Transaction) => shortid.shortId(row.from.owner as string, 12, 8)
  },
  {
    name: 'Amount 0 Deposit',
    label: t('MSG_AMOUNT_0_DEPOSIT'),
    align: 'center',
    field: (row: transaction.Transaction) => row.amount0In || '-'
  },
  {
    name: 'Amount 0 Withdraw',
    label: t('MSG_AMOUNT_0_WITHDRAW'),
    align: 'center',
    field: (row: transaction.Transaction) => row.amount0Out || '-'
  },
  {
    name: 'Amount 1 Deposit',
    label: t('MSG_AMOUNT_1_DEPOSIT'),
    align: 'center',
    field: (row: transaction.Transaction) => row.amount1In || '-'
  },
  {
    name: 'Amount 1 Withdraw',
    label: t('MSG_AMOUNT_1_WITHDRAW'),
    align: 'center',
    field: (row: transaction.Transaction) => row.amount1Out || '-'
  },
  {
    name: 'Liquidity',
    label: t('MSG_LIQUIDITY'),
    align: 'center',
    field: (row: transaction.Transaction) => row.liquidity || '-'
  },
  {
    name: 'Date',
    label: t('MSG_DATE'),
    align: 'center',
    field: (row: transaction.Transaction) => date.formatDate(row.createdAt / 1000, 'YYYY/MM/DD HH:mm:ss')
  }
])

const _pool = pool.usePoolStore()
const _swap = swap.useSwapStore()

const selectedPool = computed(() => _swap.selectedPool)
// TODO: full history with kline
const transactions = computed(() => _pool._transactions(selectedPool.value?.poolId))

const getLatestTransactions = () => {
  if (!selectedPool.value?.poolApplication) return
  _pool.latestTransactions({
    startId: _pool.nextStartId(selectedPool.value?.poolId)
  }, selectedPool.value?.poolId, selectedPool.value?.poolApplication)
}

watch(selectedPool, () => {
  getLatestTransactions()
})

onMounted(() => {
  getLatestTransactions()
})

</script>

<style scoped lang='sass'>
:deep(td)
  height: 36px !important
</style>
