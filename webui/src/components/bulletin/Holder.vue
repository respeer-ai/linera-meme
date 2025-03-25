<template>
  <div>
    <div>
      <strong>Treasure leaderboard</strong>
    </div>
    <q-separator />
    <div v-for='(item, index) in [] as Item[]' :key='item.owner.chainId' class='row decorate-dashed-border-bottom vertical-inner-y-margin'>
      <q-img
        v-if='index === 0'
        :src='trophyNo1' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='index === 1'
        :src='trophyNo2' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='index === 2'
        :src='trophyNo3' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <q-img
        v-if='index > 2'
        src='' width='15px' height='15px'
        class='cursor-pointer horizontal-inner-x-margin-right'
      />
      <div>{{ shortId(item.owner.owner, 8) }}</div>
      <q-space />
      <div>{{ Number(item.balance).toFixed(2) }} AAAAAA</div>
    </div>
  </div>
</template>
<script setup lang='ts'>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { trophyNo1, trophyNo2, trophyNo3 } from 'src/assets'
import { shortId } from 'src/utils/shortid'

interface Item {
  owner: {
    chainId: string
    owner: string
  }
  balance: number
}

const router = useRouter()

const token0 = ref('')

onMounted(() => {
  if (router.currentRoute.value.query.token0 != null) {
    token0.value = router.currentRoute.value.query.token0 as string
  }
})

</script>
