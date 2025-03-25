<template>
  <q-page>
    <q-infinite-scroll :offset='300' :style='{padding: "0 8px"}'>
      <div class='row'>
        <div v-for='item in applications' :key='item.applicationId' class='col-xs-12 col-sm-6 col-md-4'>
          <MemeCard :meme-info='item' />
        </div>
      </div>
    </q-infinite-scroll>
    <q-ajax-bar
      ref='progressBar'
      position='bottom'
      color='blue'
      size='2px'
      skip-hijack
    />
  </q-page>
</template>

<script setup lang='ts'>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { QAjaxBar } from 'quasar'
import { ams, proxy, notify } from 'src/localstore'

import MemeCard from './MemeCard.vue'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'

const _ams = ams.useAmsStore()
const _proxy = proxy.useProxyStore()
const applications = computed(() => _ams.applications.filter((el) => _proxy.chains.map((el: Chain) => el.token as string).includes(el.applicationId)))

const getMemeApplications = () => {
  _proxy.getApplications({
    Message: {
      Error: {
        Title: 'Get meme applications',
        Message: 'Failed get meme applications',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, (error: boolean, rows?: Chain[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

const getApplications = () => {
  _ams.getApplications({
    limit: 40,
    Message: {
      Error: {
        Title: 'Get applications',
        Message: 'Failed get applications',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, (error: boolean, rows?: ams.Application[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

const loadApplications = () => {
  loading.value = true
  getMemeApplications()
  getApplications()
  loading.value = false
}

const loading = ref(false)
const progressBar = ref<QAjaxBar>()

watch(loading, () => {
  if (loading.value) {
    progressBar.value?.start()
  } else {
    progressBar.value?.stop()
  }
})

const applicationRefresher = ref(-1)

onMounted(() => {
  loadApplications()
  applicationRefresher.value = window.setInterval(loadApplications, 30 * 1000)
})

onBeforeUnmount(() => {
  if (applicationRefresher.value >= 0) {
    window.clearInterval(applicationRefresher.value)
    applicationRefresher.value = -1
  }
})

</script>

<style lang='sass' scoped>
</style>
