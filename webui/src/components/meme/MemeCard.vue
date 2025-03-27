<template>
  <q-card flat class='meme-card cursor-pointer shake'>
    <q-item>
      <div class='horizontal-inner-x-margin-right vertical-card-align' avatar>
        <q-img :src='logo' width='128px' />
      </div>
      <div>
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
    </q-item>
  </q-card>
</template>

<script setup lang='ts'>
import { toRef, ref } from 'vue'
import { discordLogo, githubLogo, internetLogo, telegramLogo, twitterLogo } from 'src/assets'
import { ams, meme } from 'src/localstore'
import { _copyToClipboard } from 'src/utils/copy_to_clipboard'

interface Props {
  application: ams.Application
}

// eslint-disable-next-line no-undef
const props = defineProps<Props>()
const application = toRef(props, 'application')

const _ams = ams.useAmsStore()

const _meme = ref(JSON.parse(application.value.spec) as meme.Meme)

const logo = ref(_ams.applicationLogo(application.value))

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
