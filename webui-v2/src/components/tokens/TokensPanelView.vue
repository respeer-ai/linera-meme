<template>
  <div>
    <q-tabs
      v-model='tab'
      indicator-color='transparent'
      align='left'
    >
      <q-tab :name='Tab.Tokens' :label='Tab.Tokens' />
      <q-tab :name='Tab.Pools' :label='Tab.Pools' />
      <q-tab :name='Tab.Transactions' :label='Tab.Transactions' />
      <q-space />
      <div v-if='tab === Tab.Tokens' class='narrow-btn q-mr-md'>
        <q-btn dense no-caps rounded flat class='text-white bg-primary'>
          Join mining
        </q-btn>
        <q-icon name='help' size='20px' class='q-ml-xs cursor-pointer'>
          <q-tooltip
            class='font-size-14 bg-grey-10'
            anchor='bottom end'
            self='top end'
          >
            Join mining of new created tokens.
          </q-tooltip>
        </q-icon>
      </div>
      <div v-else-if='tab === Tab.Pools' class='narrow-btn q-mr-md'>
        <q-btn dense no-caps rounded flat class='text-white bg-primary'>
          Add liquidity
        </q-btn>
      </div>
    </q-tabs>
    <q-tab-panels
      v-model='tab'
      animated
      swipeable
      transition-prev='jump-left'
      transition-next='jump-left'
    >
      <q-tab-panel :name='Tab.Tokens'>
        <tokens-list-view />
      </q-tab-panel>
      <q-tab-panel :name='Tab.Pools'>
        <pools-list-view />
      </q-tab-panel>
      <q-tab-panel :name='Tab.Transactions'>
        <transactions-list-view />
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script setup lang='ts'>
import { onMounted, ref } from 'vue'
import { ams, swap } from 'src/stores/export'

import TokensListView from './TokensListView.vue'
import PoolsListView from './PoolsListView.vue'
import TransactionsListView from './TransactionsListView.vue'

enum Tab {
  Tokens = 'Tokens',
  Pools = 'Pools',
  Transactions = 'Transactions'
}

const tab = ref(Tab.Tokens)

onMounted(() => {
  ams.Ams.getApplications()
  swap.Swap.getPools()
})

</script>

<style scoped lang='sass'>
::v-deep(.q-tab__label)
  font-size: 16px

</style>
