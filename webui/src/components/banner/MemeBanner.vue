<template>
  <div class='banner row'>
    <q-space />
    <div class='content flex items-center'>
      <div class='flex items-center justify-center full-width'>
        <div class='slogan text-grey-9 full-width text-center'>
          Pump with <span class='text-red-6 text-bold'>Linera</span> <strong class='text-black'>Microchain</strong>
        </div>
        <div class='sub-slogan text-black full-width text-center'>
          Unleash unlimited power of next generation real-time & reactive web3 infrastructure
        </div>
        <div class='row full-width vertical-inner-y-margin'>
          <q-space />
          <q-btn
            rounded label='create new meme token now' class='bg-black text-white commit-btn' flat
            @click='onCreateMemeTokenClick'
          />
          <q-space />
        </div>
      </div>
    </div>
    <q-space />
  </div>
</template>

<script setup lang='ts'>
import { useRouter } from 'vue-router'

const router = useRouter()

const onCreateMemeTokenClick = () => {
  void router.push({ path: '/create/meme' })
}

</script>

<style scoped lang='sass'>
.banner
  background: linear-gradient($green-3, white)
  height: 480px
  width: 100%

.slogan
  font-size: 36px

.sub-slogan
  font-size: 24px

.commit-btn
  width: 400px
</style>
