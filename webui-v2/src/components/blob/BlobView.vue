<template>
  <q-img :src='url' class='text-neutral radius-8 cursor-pointer'>
    <div class='absolute-bottom text-bold full-width text-center line-height-10'>{{ ticker }}</div>
  </q-img>
</template>

<script setup lang='ts'>
import { BlobData } from 'src/__generated__/graphql/blob/graphql'
import { ams, blob as blobApi, meme } from 'src/stores/export'
import { computed, toRef } from 'vue'

interface Props {
  blob: BlobData
}
const props = defineProps<Props>()
const _blob = toRef(props, 'blob')
const url = computed(() => blobApi.Blob.blobPath(_blob.value))

const applications = computed(() => ams.Ams.applications())
const ticker = computed(() => (JSON.parse(applications.value.find((el) => el.logo === _blob.value.blobHash)?.spec || '{}') as meme.Meme)?.ticker)

</script>
