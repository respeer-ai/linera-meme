<template>
  <div>
    <div class='row items-center'>
      <section-title-view icon='water' title='Liquidity Pools' />
      <q-space />
      <div class='narrow-btn'>
        <q-btn no-caps flat dense rounded class='bg-primary'>
          <div class='row flex justify-center items-center'>
            <q-icon name='add' color='white' size='16px' />
            <span class='q-ml-xs'>Add Liquidity</span>
          </div>
        </q-btn>
        <q-btn flat dense rounded class='text-primary'>View All</q-btn>
      </div>
    </div>
    <div
      class='q-mt-md row flex flex-wrap'
      style='justify-content: center; gap: 16px; align-items: stretch;'
    >
      <div
        class='flex flex-col'
        style='
          flex: 1 1 0;
          max-width: calc((100% - 32px) / 2);
          min-width: 240px;
          display: flex;
          flex-direction: column;
        '
      >
        <swap-pair-wide-view
          :pool='pools[0] as unknown as Pool'
          style='flex: 1;'
        />
      </div>

      <div
        class='flex flex-col'
        style='
          flex: 1 1 0;
          max-width: calc((100% - 32px) / 4);
          min-width: 240px;
          display: flex;
          flex-direction: column;
        '
      >
        <swap-pair-narrow-view
          :pool='pools[1] as unknown as Pool'
          style='flex: 1;'
        />
      </div>

      <div
        class='flex flex-col'
        style='
          flex: 1 1 0;
          max-width: calc((100% - 32px) / 4);
          min-width: 240px;
          display: flex;
          flex-direction: column;
        '
      >
        <swap-pair-narrow-view
          :pool='pools[2] as unknown as Pool'
          style='flex: 1;'
        />
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { Pool } from 'src/__generated__/graphql/swap/graphql'
import { computed, onMounted } from 'vue'
import { swap, ams } from 'src/stores/export'

import SectionTitleView from '../common/SectionTitleView.vue'
import SwapPairNarrowView from './SwapPairNarrowView.vue'
import SwapPairWideView from './SwapPairWideView.vue'

const pools = computed(() => swap.pools())

onMounted(() => {
  swap.getPools()
  ams.getApplications()
})

</script>
