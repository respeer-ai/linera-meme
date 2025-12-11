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
        <div class='q-mt-md row'>
          <q-avatar size='20px' class='bg-grey-5 cursor-pointer'>
            <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/x.svg' width='16px' height='16px' />
          </q-avatar>
          <q-avatar size='20px' class='bg-grey-5 cursor-pointer q-ml-md'>
            <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/discord.svg' width='16px' height='16px' />
          </q-avatar>
          <q-avatar size='20px' class='bg-grey-5 cursor-pointer q-ml-md'>
            <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/github.svg' width='16px' height='16px' />
          </q-avatar>
          <q-avatar size='20px' class='bg-grey-5 cursor-pointer q-ml-md'>
            <q-img src='https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/telegram.svg' width='16px' height='16px' />
          </q-avatar>
        </div>
      </div>
      <q-space />
      <div>
        <div class='font-size-16 text-light text-bold'>Platform</div>
        <div class='q-mt-md text-neutral cursor-pointer'>Trade</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>Trending</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>Pools</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>Leaderboard</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>Create token</div>
      </div>
      <div class='q-ml-lg'>
        <div class='font-size-16 text-light text-bold'>Products</div>
        <div class='q-mt-md text-neutral cursor-pointer'>ResPeer</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>MicroMeme</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>CheCko</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>MaaS</div>
      </div>
      <div class='q-ml-lg'>
        <div class='font-size-16 text-light text-bold'>Docs</div>
        <div class='q-mt-md text-neutral cursor-pointer'>Linera Whitepaper CN</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>Developer Manual CN</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>MicroMeme Manual</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>CheCko Manual</div>
      </div>
      <div class='q-ml-lg'>
        <div class='font-size-16 text-light text-bold'>Legal</div>
        <div class='q-mt-md text-neutral cursor-pointer'>Term of Use</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>Privacy Policy</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>Disclaimer</div>
        <div class='q-mt-sm text-neutral cursor-pointer'>You must know</div>
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
