<template>
  <div>
    <section-title-view icon='trending_up' title='Trending Tokens' />
    <div class='q-mt-md row flex flex-wrap' style='justify-content: center; gap: 16px;'>
      <div style='flex: 1 1 0; max-width: calc((100% - 32px) / 3); min-width: 240px;'>
        <bulletin-list-view icon='trending_up' label='Top Gainers' :data='[]' />
      </div>
      <div style='flex: 1 1 0; max-width: calc((100% - 32px) / 3); min-width: 240px;'>
        <bulletin-list-view icon='pie_chart' label='Top Volume' :data='[]' />
      </div>
      <div style='flex: 1 1 0; max-width: calc((100% - 32px) / 3); min-width: 240px;'>
        <bulletin-list-view icon='rocket_launch' label='New Tokens' :data='[]' />
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>

import SectionTitleView from '../common/SectionTitleView.vue'
import BulletinListView from '../bulletin/BulletinListView.vue'

</script>
