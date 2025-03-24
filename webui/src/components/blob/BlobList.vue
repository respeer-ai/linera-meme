<template>
  <q-page class='flex justify-center'>
    <div :style='{maxWidth: "1440px"}'>
      <q-table
        flat
        :rows='rows'
        :columns='columns'
        row-key='id'
        :pagination='initialPagination'
        :style='{minWidth: "1280px"}'
      >
        <template #body-cell-thumbnail='props'>
          <q-td :props='props'>
            <q-img
              :src='props.row.thumbnail'
              :alt='props.row.blobHash'
              style='max-width: 50px; max-height: 50px;'
              contain
            />
          </q-td>
        </template>
      </q-table>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
import { onMounted, ref, computed } from 'vue'
import { BlobInfo } from 'src/stores/memeInfo'
import { ApolloClient } from '@apollo/client/core'
import gql from 'graphql-tag'
import { graphqlResult } from 'src/utils'
import { getAppClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { useI18n } from 'vue-i18n'
import { useHostStore } from 'src/mystore/host'

// eslint-disable-next-line @typescript-eslint/unbound-method
const { t } = useI18n({ useScope: 'global' })

const blobList = ref([] as Array<BlobInfo>)
const rows = computed(() => blobList.value)
const limit = ref(10)
const blobId = ref(0)

const loading = ref(false)
const lastCreatedAt = ref(0)

const initialPagination = ref({
  sortBy: 'desc',
  descending: false,
  page: 1,
  rowsPerPage: 5
})

const onGetBlobLists = () => {
  const url = useHostStore().blobGatewayApplicationPath()
  void getBlobLists(url)
}

const getBlobLists = (url: string) => {
  const appOptions = /* await */ getAppClientOptions(url)
  const appApolloClient = new ApolloClient(appOptions)
  const { /* result, refetch, fetchMore, */ onResult /*, onError */ } = provideApolloClient(appApolloClient)(() => useQuery(gql`
    query list($createdAfter: Int!,$limit: Int!){
      list(createdAfter: $createdAfter, limit: $limit){
        storeType
        blobHash
        dataType
        createdAt
        creator
      }
    }
  `, {
    createdAfter: lastCreatedAt,
    limit: limit.value
  }, {
    fetchPolicy: 'network-only'
  }))

  onResult((res) => {
    if (res.loading) return
    const apps = graphqlResult.data(res, 'list') as Array<BlobInfo>
    for (let i = 0; i < apps.length; i++) {
      const blob = {
        id: blobId.value,
        blobHash: apps[i].blobHash,
        dataType: apps[i].dataType,
        createdAt: apps[i].createdAt,
        creator: apps[i].creator,
        thumbnail: apps[i].dataType === 'IMAGE' ? useHostStore().blobDataPath(apps[i].storeType, apps[i].blobHash) : ''
      } as BlobInfo
      blobId.value += 1
      blobList.value.push(blob)
      if (lastCreatedAt.value < blob.createdAt) {
        lastCreatedAt.value = blob.createdAt
      }
    }
    loading.value = false
  })
}

onMounted(async () => {
  await Promise.resolve()
  onGetBlobLists()
})

const timeAgo = (timestamp: number): string => {
  if (timestamp === 0) {
    return 'No recent transactions'
  }
  const now = Date.now()
  const seconds = Math.floor((now / 1000) - (timestamp / 1000000))
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) {
    return seconds === 1 ? '1 second ago' : `${seconds} seconds ago`
  } else if (minutes < 60) {
    return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`
  } else if (hours < 24) {
    return hours === 1 ? '1 hour ago' : `${hours} hours ago`
  } else {
    return days === 1 ? '1 day ago' : `${days} days ago`
  }
}

const columns = computed(() => [
  {
    name: 'ID',
    label: t('MSG_ID'),
    sortable: true,
    field: (row: BlobInfo) => row.id
  },
  {
    name: 'blobHash',
    label: t('MSG_BLOB_HASH'),
    sortable: true,
    field: (row: BlobInfo) => row.blobHash
  },
  {
    name: 'dataType',
    label: t('MSG_DATATYPE'),
    sortable: true,
    field: (row: BlobInfo) => row.dataType
  },
  {
    name: 'creator',
    label: t('MSG_CREATOR'),
    sortable: true,
    field: (row: BlobInfo) => row.creator
  },
  {
    name: 'createdAt',
    label: t('MSG_CREATED_AT'),
    sortable: true,
    field: (row: BlobInfo) => timeAgo(row.createdAt)
  },
  {
    name: 'thumbnail',
    label: t('MSG_THUMBNAIL'),
    sortable: true,
    field: (row: BlobInfo) => row.thumbnail
  }
])

</script>

<style lang='sass' scoped>
</style>
