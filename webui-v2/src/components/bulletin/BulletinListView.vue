<template>
  <q-card flat class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md'>
    <div class='row items-center'>
      <q-icon :name='icon' size='20px' color='secondary' />
      <div class='q-ml-sm font-size-18 text-dark-secondary'>{{ label }}</div>
      <q-space />
      <div class='narrow-btn'>
        <q-btn flat dense rounded class='text-primary'>View All</q-btn>
      </div>
    </div>
    <div class='q-mt-md'>
      <bulletin-list-item-view v-for='(item, index) in data' :key='index' :data='item' />
    </div>
  </q-card>
</template>

<script setup lang='ts'>
import { toRef } from 'vue'
import { BulletinItem } from './BulletinItem'

import BulletinListItemView from './BulletinListItemView.vue'

interface Props {
  icon: string
  label: string
  data: BulletinItem[]
}
const props = defineProps<Props>()
const icon = toRef(props, 'icon')
const label = toRef(props, 'label')
const data = toRef(props, 'data')

</script>
