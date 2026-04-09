<template>
  <div>
    <q-tabs
      v-model='_tab'
      indicator-color='transparent'
      align='left'
    >
      <q-tab :name='Tab.Tokens' :label='Tab.Tokens' />
      <q-tab :name='Tab.Pools' :label='Tab.Pools' />
      <q-tab :name='Tab.Transactions' :label='Tab.Transactions' />
      <q-space />
      <div v-if='_tab === Tab.Tokens' class='narrow-btn q-mr-sm'>
        <q-btn v-if='false' dense no-caps rounded flat class='text-white bg-primary'>
          Join mining
        </q-btn>
        <volume-select-view v-model='volumeInterval' />
      </div>
      <div v-else-if='_tab === Tab.Pools' class='medium-btn q-mr-sm'>
        <q-btn dense no-caps flat class='text-white bg-primary radius-12' @click='onAddLiquidityClick'>
          Add liquidity
        </q-btn>
      </div>
      <div>
        <search-view @search='onSearch' />
      </div>
    </q-tabs>
    <q-tab-panels
      v-model='_tab'
      animated
      swipeable
      transition-prev='jump-left'
      transition-next='jump-left'
    >
      <q-tab-panel :name='Tab.Tokens'>
        <tokens-list-view :volume-interval='volumeInterval' />
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
import { onMounted, ref, toRef } from 'vue'
import { ams, kline, swap } from 'src/stores/export'
import { Tab } from './Tab'
import { useRouter } from 'vue-router'
import { buildAddLiquidityRoute } from '../pools/poolFlow'

import TokensListView from './TokensListView.vue'
import PoolsListView from './PoolsListView.vue'
import TransactionsListView from './TransactionsListView.vue'
import SearchView from 'src/components/search/SearchView.vue'
import VolumeSelectView from './VolumeSelectView.vue'

interface Props {
  tab: Tab
}
const props = defineProps<Props>()
const tab = toRef(props, 'tab')
const router = useRouter()

const _tab = ref(tab.value)
const volumeInterval = ref(kline.TickerInterval.OneDay)

onMounted(() => {
  ams.Ams.getApplications()
  swap.Swap.getPools()
})

const onSearch = (keyword: string) => {
  console.log(keyword)
}

const onAddLiquidityClick = () => {
  void router.push(buildAddLiquidityRoute())
}

</script>

<style scoped lang='sass'>
::v-deep(.q-tab__label)
  font-size: 16px

::v-deep(.q-tab-panel)
  padding-right: 4px !important
  padding-left: 4px !important

</style>
