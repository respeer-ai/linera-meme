<template>
  <q-card bordered flat class='meme-card cursor-pointer shake'>
    <div class='text-center meme-card-banner' avatar>
      <q-img :src='logo' width='128px' />
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
          {{ transactionDisplay }}
        </div>
      </q-item-label>
      <q-item-label caption>
        <div class='row vertical-section-y-margin'>
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
import { timestamp, shortid } from 'src/utils'
import { useI18n } from 'vue-i18n'

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
const transactionDisplay = computed(() => {
  if (!transaction.value) return ''
  const _transaction = transaction.value?.transaction as swap.Transaction
  const _timestamp = timestamp.timestamp2HumanReadable(_transaction.createdAt)
  return shortid.shortId(_transaction.from.owner as string, 12) + ' ' + _transaction.transactionType.toString() + ' ' + t(_timestamp.msg, { VALUE: _timestamp.value })
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
  padding: 16px
</style>
