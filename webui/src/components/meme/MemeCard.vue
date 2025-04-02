<template>
  <q-card bordered flat class='meme-card cursor-pointer shake'>
    <div class='text-center meme-card-banner' avatar>
      <q-img
        :src='logo' width='100%' height='100%'
        fit='contain'
      />
    </div>
    <div class='meme-info'>
      <q-item-label class='text-h6'>
        <q-badge color='green-6'>
          {{ _meme.ticker }}
        </q-badge>
        {{ application.applicationName }}
        <q-icon name='bi-copy' size='16px' :style='{marginTop: "-3px"}' @click.stop='(evt) => _copyToClipboard(application.applicationId, evt)' />
      </q-item-label>
      <q-item-label>
        <div class='vertical-inner-y-margin'>
          {{ application.description }}
        </div>
      </q-item-label>
      <q-item-label>
        <div class='vertical-inner-y-margin'>
          <div v-if='transactionUser' class='row meme-info-inner'>
            <span class='label text-grey-8'>Last Transaction</span>
            <span>
              <div class='text-bold text-grey-9'>{{ transactionUser }}</div>
              <div class='text-grey-8' :style='{marginTop: "2px", marginBottom: "2px"}'>{{ transactionInfo }}</div>
            </span>
          </div>
          <div v-if='price' class='row meme-info-inner'>
            <span class='label text-grey-8'>{{ _meme.ticker }}/{{ constants.LINERA_TICKER }}</span> {{ price }} {{ constants.LINERA_TICKER }}
          </div>
          <div v-if='marketCapacity' class='row meme-info-inner'>
            <span class='label text-grey-8'>Market Capacity</span> {{ marketCapacity }} {{ constants.LINERA_TICKER }}
          </div>
          <div class='row meme-info-inner'>
            <span class='label text-grey-8'>Total Supply</span> {{ _meme.totalSupply }} {{ _meme.ticker }}
          </div>
          <div class='row meme-info-inner'>
            <span class='label text-grey-8'>Initial Liquidity</span>
            <span class='content'>
              <div class='row'>
                <div class='text-bold text-grey-9'>{{ initialLiquidity }}</div>
                <div class='horizontal-inner-x-margin-left text-grey-8'>{{ initialLiquidityValue }}</div>
                <q-tooltip anchor='bottom middle' self='top middle' :offset='[10, 10]'>
                  <strong>{{ initialLiquidity }}</strong> {{ liquidityDescription }}
                  <div v-html='miningDescription' />
                </q-tooltip>
              </div>
            </span>
          </div>
        </div>
      </q-item-label>
      <q-item-label caption>
        <div class='row vertical-section-y-margin' v-if='showCaption'>
          <q-img
            v-if='_meme.metadata.github?.length' :src='githubLogo' width='20px' height='20px'
            class='cursor-pointer horizontal-inner-x-margin-right'
          />
          <q-img
            v-if='_meme.metadata.discord?.length' :src='discordLogo' width='20px' height='20px'
            class='cursor-pointer horizontal-inner-x-margin-right'
          />
          <q-img
            v-if='_meme.metadata.twitter?.length' :src='twitterLogo' width='20px' height='20px'
            class='cursor-pointer horizontal-inner-x-margin-right'
          />
          <q-img
            v-if='_meme.metadata.telegram?.length' :src='telegramLogo' width='20px' height='20px'
            class='cursor-pointer horizontal-inner-x-margin-right'
          />
          <q-img
            v-if='_meme.metadata.website?.length' :src='internetLogo' width='20px' height='20px'
            class='cursor-pointer'
          />
          <q-img
            v-if='_meme.metadata.liveStream?.length' :src='internetLogo' width='20px' height='20px'
            class='cursor-pointer'
          />
        </div>
        <div class='row vertical-section-y-margin' v-else>
          Creator didn't leave any social information!
        </div>
      </q-item-label>
    </div>
  </q-card>
</template>

<script setup lang='ts'>
import { toRef, ref, computed } from 'vue'
import { discordLogo, githubLogo, internetLogo, telegramLogo, twitterLogo } from 'src/assets'
import { ams, meme, swap } from 'src/localstore'
import { _copyToClipboard } from 'src/utils/copy_to_clipboard'
import { timestamp, shortid, formalizeFloat } from 'src/utils'
import { useI18n } from 'vue-i18n'
import { constants } from 'src/constant'

const { t } = useI18n({ useScope: 'global' })

interface Props {
  application: ams.Application
}

// eslint-disable-next-line no-undef
const props = defineProps<Props>()
const application = toRef(props, 'application')

const _ams = ams.useAmsStore()
const _swap = swap.useSwapStore()

const _meme = ref(JSON.parse(application.value.spec) as meme.Meme)
const logo = ref(_ams.applicationLogo(application.value))

const transaction = computed(() => _swap.latestTransaction(application.value.applicationId))
const transactionUser = computed(() => transaction.value ? shortid.shortId(transaction.value.from.owner as string, 12) : undefined)
const transactionInfo = computed(() => {
  if (!transaction.value) return undefined
  const _timestamp = timestamp.timestamp2HumanReadable(transaction.value.createdAt)
  return transaction.value.transactionType.toString() + ' ' + t(_timestamp.msg, { VALUE: _timestamp.value })
})

const showCaption = computed(() => {
  return _meme.value.metadata.github?.length ||
         _meme.value.metadata.twitter?.length ||
         _meme.value.metadata.website?.length ||
         _meme.value.metadata.discord?.length ||
         _meme.value.metadata.telegram?.length ||
         _meme.value.metadata.liveStream?.length
})

const price = computed(() => _swap.price(application.value.applicationId))
const marketCapacity = computed(() => price.value?.length ? formalizeFloat.trimZeros((Number(price.value) * Number(_meme.value.totalSupply)).toFixed(8)) : undefined)
const initialLiquidityValue = computed(() => _meme.value.initialLiquidity ? `${_meme.value.initialLiquidity.fungibleAmount} ${_meme.value.ticker}/${_meme.value.initialLiquidity.nativeAmount} ${constants.LINERA_TICKER}` : '')
const initialLiquidity = computed(() => _meme.value.initialLiquidity ? _meme.value.virtualInitialLiquidity ? 'Virtual' : 'Real' : 'None')
const liquidityDescription = computed(() => {
  switch (initialLiquidity.value) {
    case 'Virtual': return "means creator didn't pay for initial liquidity."
    case 'Real': return 'means creator paid for initial liquidity.'
    case 'None': default: return 'means this meme is for mining only.'
  }
})
const liquidityPercent = computed(() => _meme.value.initialLiquidity ? Number(_meme.value.initialLiquidity.fungibleAmount) / Number(_meme.value.totalSupply) : 0)
const miningDescription = computed(() => {
  if (initialLiquidity.value === 'None') return ''
  if (liquidityPercent.value >= 1) {
    return 'This token is for <strong>mining only</strong>.'
  }
  return `<strong>${((1 - liquidityPercent.value) * 100).toFixed(0)}%</strong> of total supply is for mining.`
})

</script>

<style lang='sass' scoped>
.meme-card
  border: 1px solid $red-4
  border-radius: 16px
  .q-badge
    font-size: 16px

.meme-card:hover
  background: $grey-2
  transition: 1s

.meme-card-banner
  background: $grey-3
  height: 128px

.meme-info
  padding: 24px 16px

.meme-info-inner
  border-bottom: 1px dashed $grey-4
  padding: 4px 0 0 0
  .label
    width: 180px
  .change
    font-size: 12px
    margin-left: 6px
  .content
    width: calc(100% - 180px)
</style>
