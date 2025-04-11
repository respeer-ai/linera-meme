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
import { useI18n } from 'vue-i18n'
import { swap, transaction, kline } from 'src/localstore'
import { shortid } from 'src/utils'

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

const transactions = computed(() => _kline._transactions(selectedToken0.value, selectedToken1.value))

const getTransactions = (startAt: number) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  const endAt = startAt + 3600

  _kline.getTransactions({
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt
  }, (error: boolean, rows?: transaction.TransactionExt[]) => {
    if (error || !rows?.length) return
    setTimeout(() => {
      getTransactions(endAt)
    }, 100)
  })
}

const getPoolTransactions = () => {
  if (selectedPool.value?.createdAt) {
    getTransactions(Math.floor(selectedPool.value?.createdAt / 1000000))
  }
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

onMounted(() => {
  getPoolTransactions()
})

</script>

<style scoped lang='sass'>
:deep(td)
  height: 36px !important
</style>
