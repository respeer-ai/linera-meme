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
          <td :props='props' class='text-center'>0 TLINERA</td>
          <td :props='props' class='text-center'>
            <q-icon name='arrow_drop_down' color='red-4' size='16px' />
            1.23%
          </td>
          <td :props='props' class='text-center'>
            <q-icon name='arrow_drop_down' color='red-4' size='16px' />
            2.34%
          </td>
          <td :props='props' class='text-center'>$10.23B</td>
          <td :props='props' class='text-center'>$1.23B</td>
          <!-- td :props='props' class='text-center'>0 TLINERA</td -->
          <td :props='props' class='text-center'>
            <div class='narrow-btn'>
              <q-btn dense no-caps rounded flat class='text-secondary' disable>
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
import { ams, meme, swap } from 'src/stores/export'
import { computed, ref } from 'vue'
import { Pool } from 'src/__generated__/graphql/swap/graphql'

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
