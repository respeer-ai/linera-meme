<template>
  <div>
    <div>
      <strong>24 Hour Volume leaderboard</strong>
    </div>
    <q-separator />
    <div v-for='(info, idx) in bulletinStore.TokenVolumns' :key='idx' class='row decorate-dashed-border-bottom vertical-inner-y-margin'>
      <q-img
        v-if='idx === 0'
        :src='trophyNo1' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='idx === 1'
        :src='trophyNo2' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='idx === 2'
        :src='trophyNo3' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='idx > 2'
        src='' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <div>{{ shortId(info.Address,8) }}</div>
      <q-space />
      <div>{{ Number(info.Amount).toFixed(2) }} WLINERA</div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { useBulletinStore } from 'src/mystore/bulletin'
import { shortId } from 'src/utils/shortid'
import { trophyNo1, trophyNo2, trophyNo3 } from 'src/assets'
import { onMounted, computed, watch } from 'vue'
import { useSwapStore } from 'src/mystore/swap'

const bulletinStore = useBulletinStore()
const selectedToken = computed(() => useSwapStore().SelectedToken)

watch(selectedToken, () => {
  bulletinStore.getOneDayVolumn()
})

onMounted(() => {
  bulletinStore.getOneDayVolumn()
})
</script>
