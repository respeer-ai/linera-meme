<template>
  <div class='banner row'>
    <q-space />
    <div class='content flex items-center'>
      <div class='flex items-center justify-center full-width'>
        <div class='slogan text-grey-9 full-width text-center'>
          Blob Data Indexer on <span class='text-red-6 text-bold'>Linera</span>
        </div>
        <br>
        <div class='sub-slogan text-black full-width text-center'>
          Automatically replicate data all over the world with Linera blob storage
        </div>
      </div>
    </div>
    <q-space />
  </div>
</template>

<script setup lang='ts'>
</script>

<style scoped lang='sass'>
.banner
  background: linear-gradient($blue-3, white)
  height: 480px
  width: 100%

.slogan
  font-size: 36px

.sub-slogan
  font-size: 24px
</style>
