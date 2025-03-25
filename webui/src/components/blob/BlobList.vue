<template>
  <q-page class='flex justify-center'>
    <div :style='{maxWidth: "1440px"}'>
      <q-table
        flat
        :rows='[]'
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
import { useI18n } from 'vue-i18n'

// eslint-disable-next-line @typescript-eslint/unbound-method
const { t } = useI18n({ useScope: 'global' })

const initialPagination = ref({
  sortBy: 'desc',
  descending: false,
  page: 1,
  rowsPerPage: 5
})

onMounted(async () => {
  await Promise.resolve()
})

const columns = computed(() => [
  {
    name: 'ID',
    label: t('MSG_ID'),
    sortable: true,
    field: 'ID'
  },
  {
    name: 'blobHash',
    label: t('MSG_BLOB_HASH'),
    sortable: true,
    field: 'BlobHash'
  },
  {
    name: 'dataType',
    label: t('MSG_DATATYPE'),
    sortable: true,
    field: 'DataType'
  },
  {
    name: 'creator',
    label: t('MSG_CREATOR'),
    sortable: true,
    field: 'Creator'
  },
  {
    name: 'createdAt',
    label: t('MSG_CREATED_AT'),
    sortable: true,
    field: 'CreatedAt'
  },
  {
    name: 'thumbnail',
    label: t('MSG_THUMBNAIL'),
    sortable: true,
    field: 'Thumbnail'
  }
])

</script>

<style lang='sass' scoped>
</style>
