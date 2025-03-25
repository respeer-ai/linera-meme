<template>
  <q-table
    flat
    :columns='(columns as never)'
    :rows='[]'
    :rows-per-page-options='[10]'
  />
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { date } from 'quasar'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

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
    field: 'Deposit' // 'Withdraw'
  },
  {
    name: 'Amount',
    label: t('MSG_AMOUNT'),
    align: 'center',
    field: 0
  },
  {
    name: 'Date',
    label: t('MSG_DATE'),
    align: 'center',
    field: date.formatDate(12345 * 1000, 'YYYY/MM/DD HH:mm:ss')
  }
])

</script>

<style scoped lang='sass'>
:deep(td)
  height: 36px !important
</style>
