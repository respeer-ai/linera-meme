<template>
  <div>
    <div class='row border-bottom-primary-twelve q-pb-lg'>
      <div>
        <logo-view :show-subtitle='false' />
        <div
          class='q-mt-md text-neutral'
          style='max-width: 320px;'>
          The ultimate meme trading and mining platform on Linera. Trade, create, mine, and earn meme tokens with your microchains.
        </div>
        <div class='q-mt-md footer-socials'>
          <a
            class='footer-social-link'
            href='https://x.com/respeer_ai'
            target='_blank'
            rel='noopener noreferrer'
            aria-label='ResPeer X account'
          >
            <q-avatar size='20px' class='bg-grey-5 cursor-pointer'>
              <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/x.svg' width='16px' height='16px' />
            </q-avatar>
          </a>
          <span class='footer-social-link'>
            <q-avatar size='20px' class='bg-grey-5 cursor-pointer'>
              <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/discord.svg' width='16px' height='16px' />
            </q-avatar>
          </span>
          <a
            class='footer-social-link'
            href='https://github.com/respeer-ai/linera-meme.git'
            target='_blank'
            rel='noopener noreferrer'
            aria-label='MicroMeme GitHub repository'
          >
            <q-avatar size='20px' class='bg-grey-5 cursor-pointer'>
              <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/github.svg' width='16px' height='16px' />
            </q-avatar>
          </a>
          <span class='footer-social-link'>
            <q-avatar size='20px' class='bg-grey-5 cursor-pointer'>
              <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/telegram.svg' width='16px' height='16px' />
            </q-avatar>
          </span>
        </div>
      </div>
      <q-space />
      <div>
        <div class='font-size-16 text-light text-bold'>Product</div>
        <a
          class='q-mt-md text-neutral footer-link'
          href='https://github.com/respeer-ai/linera-wallet.git'
          target='_blank'
          rel='noopener noreferrer'
        >CheCko</a>
        <a
          class='q-mt-sm text-neutral footer-link'
          href='https://github.com/respeer-ai/linera-protocol.git'
          target='_blank'
          rel='noopener noreferrer'
        >MaaS</a>
      </div>
      <div class='q-ml-lg'>
        <div class='font-size-16 text-light text-bold'>Legal</div>
        <div class='q-mt-md text-neutral'>Terms of Use</div>
        <div class='q-mt-sm text-neutral'>Privacy Policy</div>
      </div>
    </div>
    <div class='row q-pt-lg'>
      <div class='text-neutral'>
        © 2025 MicroMeme by respeer.ai. All rights reserved.
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>

import LogoView from '../logo/LogoView.vue'

</script>

<style scoped lang='sass'>
.footer-socials
  display: flex
  align-items: center
  gap: 16px

.footer-social-link
  width: 20px
  height: 20px
  display: inline-flex
  align-items: center
  justify-content: center
  line-height: 0
  text-decoration: none

.footer-link
  display: block
  text-decoration: none

.footer-link:hover
  color: var(--q-light) !important
</style>
