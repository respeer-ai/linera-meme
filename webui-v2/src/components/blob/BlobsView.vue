<template>
  <div>
    <section-title-view icon='photo' title='Blobs' />
    <div class='border-dark-secondary radius-8 bg-dark-secondary q-pa-md q-mt-md'>
      <BlobView
        v-for='(_blob, index) in blobs'
        :key='index'
        :blob='_blob'
        style='width: 20%;'
        :class='[ index === 0 ? "" : "q-ml-md", blobs.length > 4 ? "q-mb-md" : "" ]'
      />
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted } from 'vue'
import { blob } from 'src/stores/export'

import SectionTitleView from '../common/SectionTitleView.vue'
import BlobView from './BlobView.vue'

const blobs = computed(() => blob.Blob.blobs())

onMounted(() => {
  blob.Blob.getBlobsList()
})

</script>
