<template>
  <q-card flat :class='newTx ? "meme-card cursor-pointer shake" : "meme-card cursor-pointer"' @click='onSwap(memeInfo.appID)'>
    <q-item>
      <div class='horizontal-inner-x-margin-right vertical-card-align' avatar>
        <q-img :src='processImg(memeInfo.logoStoreType, memeInfo.logo)' width='128px' />
      </div>

      <div>
        <q-item-label class='text-h6'>
          <q-badge color='green-6'>
            {{ memeInfo.ticker }}
          </q-badge>
          {{ memeInfo.appName }}
          <q-icon name='bi-copy' size='16px' :style='{marginTop: "-3px"}' @click.stop='(evt) => _copyToClipboard(memeInfo.appID, evt)' />
        </q-item-label>
        <q-item-label>
          <div class='vertical-inner-y-margin'>
            {{ memeInfo.description }}
          </div>
        </q-item-label>
        <q-item-label>
          <div class='vertical-inner-y-margin'>
            <div class='row meme-info'>
              <span class='label text-grey-8'>Last Transaction</span> {{ timeAgo(memeInfo.lastTxAt) }}, {{ Number(memeInfo.lastTxOneAmount).toFixed(2) }} WTLINERA
            </div>
            <div class='row meme-info'>
              <span class='label text-grey-8'>Last 24H Volume</span> {{ Number(memeInfo.oneDayOneAmountVolumn).toFixed(6) }} WTLINERA
            </div>
            <div class='row meme-info'>
              <span class='label text-grey-8'>{{ memeInfo.ticker }}/WTLINERA</span> {{ Number(memeInfo.nowPrice).toFixed(6) }} WLINERA <span :class='Number(memeInfo.oneDayIncresePercent) < 0 ? "change text-red" : "change text-green"'>{{ Number(memeInfo.oneDayIncresePercent) >= 0 ? "+" : "" }}{{ Number(memeInfo.oneDayIncresePercent).toFixed(2) }}%</span>
            </div>
            <div class='row meme-info'>
              <span class='label text-grey-8'>Market Capacity</span> {{ (Number(memeInfo.initialSupply) * Number(memeInfo.nowPrice)).toFixed(6) }} WTLINERA
            </div>
          </div>
        </q-item-label>
        <q-item-label caption>
          <div class='row vertical-section-y-margin'>
            <q-img
              v-if='memeInfo.github' :src='githubLogo' width='20px' height='20px'
              class='cursor-pointer horizontal-inner-x-margin-right'
              @click='goLink(memeInfo.github, $event)'
            />
            <q-img
              v-if='memeInfo.discord?.length > 0' :src='discordLogo' width='20px' height='20px'
              class='cursor-pointer horizontal-inner-x-margin-right'
              @click='goLink(memeInfo.discord, $event)'
            />
            <q-img
              v-if='memeInfo.twitter?.length > 0' :src='twitterLogo' width='20px' height='20px'
              class='cursor-pointer horizontal-inner-x-margin-right'
              @click='goLink(memeInfo.twitter, $event)'
            />
            <q-img
              v-if='memeInfo.telegram?.length > 0' :src='telegramLogo' width='20px' height='20px'
              class='cursor-pointer horizontal-inner-x-margin-right'
              @click='goLink(memeInfo.telegram, $event)'
            />
            <q-img
              v-if='memeInfo.website?.length > 0' :src='internetLogo' width='20px' height='20px'
              class='cursor-pointer'
              @click='goLink(memeInfo.website, $event)'
            />
          </div>
        </q-item-label>
      </div>
    </q-item>
  </q-card>
</template>

<script setup lang='ts'>
import { toRef, ref, watch } from 'vue'
import { MemeAppInfoDisplay } from 'src/stores/memeInfo'
import { discordLogo, githubLogo, internetLogo, telegramLogo, twitterLogo } from 'src/assets'
import { useRouter } from 'vue-router'
import { useHostStore } from 'src/mystore/host'
import { copyToClipboard } from 'quasar'
import { notification } from 'src/mystore'

interface Props {
  memeInfo: MemeAppInfoDisplay
}
const props = defineProps<Props>()
const memeInfo = toRef(props, 'memeInfo')
const newTx = ref(true)

const router = useRouter()

const _notification = notification.useNotificationStore()

const _copyToClipboard = (
  content: string,
  evt: {
    preventDefault(): unknown
    clipboardData: { getData: (arg0: string) => string }
  }
) => {
  evt.preventDefault()
  copyToClipboard(content)
    .then(() => {
      _notification.pushNotification({
        Title: 'Copy content',
        Message: `Success copy ${content.substring(0, 20)}... to clipboard.`,
        Popup: true,
        Type: notification.NotifyType.Info
      })
    })
    .catch((e) => {
      _notification.pushNotification({
        Title: 'Copy content',
        // eslint-disable-next-line @typescript-eslint/restrict-template-expressions
        Message: `Failed copy ${content.substring(0, 20)}...: ${e}`,
        Popup: true,
        Type: notification.NotifyType.Error
      })
    })
}

const onSwap = (token0: string) => {
<<<<<<< HEAD
  if (memeInfo.value.poolCreated) {
    void router.push({
      path: '/swap',
      query: {
        token0,
        token1: useHostStore().wlineraApplicationId
      }
    })
  } else {
    void router.push({
      path: '/add/liquidity',
      query: {
        token0Id: memeInfo.value.appID,
        token0Ticker: memeInfo.value.ticker
      }
    })
  }
=======
  void router.push({
    path: 'swap',
    query: {
      token0,
      token1: useHostStore().wlineraApplicationId
    }
  })
>>>>>>> 8c1ba0598ede6fc73a5d2a4008bf8af677aaf286
}

const goLink = (url: string, event: MouseEvent) => {
  event.stopPropagation()
  window.open(url, '_blank')
}

const processImg = (storeType: string, imageHash: string): string => {
  return useHostStore().blobDataPath(storeType, imageHash)
}

const timeAgo = (timestamp: number): string => {
  if (timestamp === 0) {
    return 'No recent transactions'
  }
  const now = Date.now()
  const seconds = Math.floor((now / 1000) - timestamp)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) {
    return seconds === 1 ? '1 second ago' : `${seconds} seconds ago`
  } else if (minutes < 60) {
    return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`
  } else if (hours < 24) {
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`
  } else {
    return days === 1 ? '1 day ago' : `${days} days ago`
  }
}

const sleep = async (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms))
}

watch(
  () => memeInfo.value.lastTxAt,
  async () => {
    newTx.value = true
    await sleep(1000)
    newTx.value = false
  }
)

</script>

<style lang='sass' scoped>
.meme-card
  border: 1px solid transparent
  border-bottom: 1px solid $red-1
  padding: 16px
  border-radius: 16px
  .q-badge
    font-size: 16px

.meme-card:hover
  border: 1px solid $red-4
  transition: 1s

.meme-info
  border-bottom: 1px dashed $grey-4
  padding: 4px 0 0 0
  .label
    width: 180px
  .change
    font-size: 12px
    margin-left: 6px
</style>
