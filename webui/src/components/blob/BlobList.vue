<template>
  <q-page class='flex justify-center'>
    <div :style='{maxWidth: "960px"}'>
      <q-table
        flat
        :rows='blobs'
        :columns='(columns as never)'
        row-key='id'
        :pagination='initialPagination'
        :style='{minWidth: "960px"}'
      >
        <template #body-cell-thumbnail='props'>
          <q-td :props='props'>
            <q-img
              :src='_blob.blobPath(props.row)'
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
import { useI18n } from 'vue-i18n'
import { blob, notify, account } from 'src/localstore'
import { BlobData } from 'src/__generated__/graphql/blob/graphql'
import { shortid, timestamp } from 'src/utils'

// eslint-disable-next-line @typescript-eslint/unbound-method
const { t } = useI18n({ useScope: 'global' })

const initialPagination = ref({
  sortBy: 'desc',
  descending: false,
  page: 1,
  rowsPerPage: 5
})

const _blob = blob.useBlobStore()
const blobs = computed(() => _blob.blobs)

const listBlobs = (createdAfter: number) => {
  _blob.listBlobs({
    createdAfter,
    limit: 40,
    Message: {
      Error: {
        Title: 'List blobs',
        Message: 'Failed list blobs',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, (error: boolean, rows?: BlobData[]) => {
    if (error || !rows?.length) return
    listBlobs(Math.max(...rows.map((el) => el.createdAt as number)))
  })
}

onMounted(() => {
  listBlobs(0)
})

const columns = computed(() => [
  {
    name: 'blobHash',
    label: t('MSG_BLOB_HASH'),
    align: 'left',
    sortable: true,
    field: (row: BlobData) => shortid.shortId(row.blobHash as string, 12, 12)
  },
  {
    name: 'dataType',
    label: t('MSG_DATATYPE'),
    sortable: true,
    field: (row: BlobData) => row.dataType
  },
  {
    name: 'creator',
    label: t('MSG_CREATOR'),
    sortable: true,
    field: (row: BlobData) => shortid.shortId((row.creator as account.Account).owner as string, 16, 12)
  },
  {
    name: 'createdAt',
    label: t('MSG_CREATED_AT'),
    sortable: true,
    field: (row: BlobData) => {
      const createdAt = timestamp.timestamp2HumanReadable(row.createdAt as number)
      return t(createdAt.msg, { VALUE: createdAt.value })
    }
  },
  {
    name: 'thumbnail',
    label: t('MSG_THUMBNAIL'),
    sortable: false,
    field: (row: BlobData) => _blob.blobPath(row)
  }
])

</script>

<style lang='sass' scoped>
</style>
