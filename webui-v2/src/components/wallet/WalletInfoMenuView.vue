<template>
  <div>
    <div class='row items-center'>
      <q-avatar size='64px' class='bg-glass'>
        <q-icon name='account_tree' color='secondary' width='64px' height='64px' />
        <q-badge dense floating class='bg-transparent' style='padding: 12px 12px 0 0;'>
          <q-avatar size='16px' class='bg-light'>
            <q-img :src='constants.CHECKO_LOGO' width='16px' height='16px' />
          </q-avatar>
        </q-badge>
      </q-avatar>
      <q-space />
      <div class='cursor-pointer'>
        <q-icon name='settings' size='20px' color='neutral' />
      </div>
      <div class='q-ml-md cursor-pointer'>
        <q-icon name='power_settings_new' size='20px' color='neutral' />
      </div>
    </div>
    <div class='q-mt-sm text-neutral text-bold font-size-16'>
      {{ shortid.shortId(publicKey, 6, 4) }}
    </div>
    <div class='q-mt-lg text-light font-size-24'>
      TLINERA {{ balance }}
    </div>
    <div class='text-neutral text-bold font-size-16 row items-center'>
      <div style='margin-left: -8px;'>
        <q-icon name='arrow_drop_down' size='32px' color='primary' />
      </div>
      <div>
        $ 2.23 (0.32%)
      </div>
    </div>
    <div class='q-mt-md row'>
      <q-card flat style='width: calc(50% - 4px);' class='bg-primary-12 radius-8 text-primary q-pa-sm cursor-pointer'>
        <q-icon name='send' color='primary' size='20px' />
        <div class='text-bold q-mt-xs'>Send</div>
      </q-card>
      <q-space />
      <q-card flat style='width: calc(50% - 4px);' class='bg-primary-12 radius-8 text-primary q-pa-sm cursor-pointer'>
        <q-icon name='arrow_downward' color='primary' size='24px' />
        <div class='text-bold q-mt-xs'>Receive</div>
      </q-card>
    </div>
    <div class='q-mt-md narrow-btn'>
      <q-btn rounded no-caps flat class='full-width border-neutral-25 text-neutral'>
        Portfolio overview
        <div class='q-ml-sm'>
          <q-icon name='arrow_forward' size='18px' />
        </div>
      </q-btn>
    </div>
    <div class='q-mt-lg'>
      <div class='text-neutral font-size-16'>
        Latest activities
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { constants } from 'src/constant'
import { user } from 'src/stores/export'
import { shortid } from 'src/utils'
import { computed } from 'vue'

const publicKey = computed(() => user.User.publicKey())
const balance = computed(() => user.User.balance())

</script>
