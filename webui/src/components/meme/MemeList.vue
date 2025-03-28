<template>
  <q-page class='flex justify-center'>
    <q-infinite-scroll :offset='300' :style='{maxWidth: "1440px"}'>
      <div class='row'>
        <div
          v-for='(application, index) in applications'
          :key='application.applicationId'
          class='col-xs-12 col-sm-6 col-md-4'
          :style='{marginLeft: index % 3 != 0 ? "12px" : "0", width: "472px"}'
          @click='onTokenClick(application)'
        >
          <MemeCard :application='application' />
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
import { ams, proxy, notify, swap } from 'src/localstore'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'
import { useRouter } from 'vue-router'
import { constants } from 'src/constant'

import MemeCard from './MemeCard.vue'

const _ams = ams.useAmsStore()
const _proxy = proxy.useProxyStore()
const _swap = swap.useSwapStore()

const applications = computed(() => _ams.applications.filter((el) => _proxy.chains.map((_el: Chain) => _el.token as string).includes(el.applicationId)))

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

const getPools = () => {
  _swap.getPools({
    Message: {
      Error: {
        Title: 'Get latest transactions',
        Message: 'Failed get latest transactions',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  })
}

const loadApplications = () => {
  loading.value = true
  getMemeApplications()
  getApplications()
  getPools()
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

const router = useRouter()

const onTokenClick = (application: ams.Application) => {
  void router.push({
    path: 'swap',
    query: {
      token0: application.applicationId,
      token1: constants.LINERA_NATIVE_ID
    }
  })
}

</script>

<style lang='sass' scoped>
</style>
