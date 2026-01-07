<template>
  <div class='row items-center q-py-sm text-neutral'>
    <q-icon :name='icon' size='24px' :color='color' />
    <div class='q-ml-sm' style='width: 400px'>{{ shortid.shortId(data.account.chain_id, 24, 24) }}</div>
    <div v-if='data.account.owner' class='q-ml-sm' style='width: 400px'>{{ shortid.shortId(data.account.owner, 24, 24) }}</div>
    <q-space />
    <div class='q-ml-sm text-right' style='width: 140px'><strong class='text-light'>{{ Number(data.amount).toFixed(4) }}</strong> {{ ticker }}</div>
    <div class='q-ml-sm text-right' style='width: 140px'><strong class='text-light'>{{ Number(tokenValue).toFixed(4) }}</strong> {{ constants.LINERA_TICKER }}</div>
  </div>
</template>

<script setup lang='ts'>
import { constants } from 'src/constant'
import { account } from 'src/stores/export'
import { shortid } from 'src/utils'
import { computed, toRef } from 'vue'

interface Props {
  data: { account: account.Account, amount: string }
  ticker: string
  position: number
  applicationHolder: boolean
  poolHolder: boolean
  tokenValue: string
}
const props = defineProps<Props>()
const data = toRef(props, 'data')
const ticker = toRef(props, 'ticker')
const position = toRef(props, 'position')
const applicationHolder = toRef(props, 'applicationHolder')
const poolHolder = toRef(props, 'poolHolder')
const tokenValue = toRef(props, 'tokenValue')

const positionColor = () => {
  switch (position.value) {
    case 0: return 'orange'
    case 1: return 'silver'
    case 2: return 'brozen'
    default: return 'grey'
  } 
}

const color = computed(() => applicationHolder.value ? 'blue' : poolHolder.value? 'green' : positionColor())
const icon = computed(() => applicationHolder.value || poolHolder.value ? 'local_atm' : 'workspace_premium')

</script>
