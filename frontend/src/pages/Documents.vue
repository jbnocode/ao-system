<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Button
          variant="solid"
          icon-left="lucide-plus"
          :label="__('Upload')"
          @click="openUpload"
        />
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-white">
      <div
        class="flex flex-wrap items-center gap-2 border-b border-outline-gray-modals px-4 py-3"
      >
        <TextInput
          v-model="search"
          type="text"
          size="sm"
          class="w-56"
          :placeholder="__('Search files')"
          :debounce="200"
        />
        <p class="text-p-sm text-ink-gray-5">
          {{ __('Files attached to {0}.', [casesLabel]) }}
        </p>
        <div class="ml-auto">
          <Button
            size="sm"
            variant="ghost"
            icon="lucide-refresh-cw"
            :aria-label="__('Refresh')"
            :loading="list.loading"
            @click="list.reload()"
          />
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <div
          v-if="list.loading && !rows.length"
          class="flex justify-center py-16"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div
          v-else-if="!rows.length"
          class="px-4 py-12 text-center text-p-sm text-ink-gray-5"
        >
          {{
            __(
              'No documents yet. Upload a file and link it to a Case, or attach from the Case Attachments tab.',
            )
          }}
          <div class="mt-3">
            <Button
              variant="solid"
              size="sm"
              :label="__('Upload')"
              @click="openUpload"
            />
          </div>
        </div>
        <div v-else class="divide-y divide-outline-gray-modals">
          <div
            v-for="row in filteredRows"
            :key="row.name"
            class="flex w-full items-center gap-3 px-4 py-3"
          >
            <button
              type="button"
              class="min-w-0 flex-1 text-left transition hover:opacity-80"
              @click="openFile(row)"
            >
              <div class="truncate text-p-base-medium text-ink-gray-9">
                {{ row.file_name || row.name }}
              </div>
              <div class="mt-0.5 text-p-sm text-ink-gray-5">
                <template v-if="row.attached_to_name">
                  {{ row.attached_to_name }} ·
                </template>
                {{ formatSize(row.file_size) }}
                <template v-if="row.file_type">
                  · {{ row.file_type }}
                </template>
              </div>
            </button>
            <Button
              size="sm"
              variant="ghost"
              :label="__('Open {0}', [caseSingular])"
              :disabled="!row.attached_to_name"
              @click="openCase(row)"
            />
          </div>
        </div>
        <div
          v-if="filteredRows.length === 0 && rows.length"
          class="px-4 py-10 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No files match your search.') }}
        </div>
      </div>
    </div>

    <Dialog
      v-model:open="showUpload"
      :title="__('Upload to {0}', [caseSingular])"
    >
      <template #default>
        <div class="space-y-4">
          <Link
            v-model="uploadDeal"
            doctype="CRM Deal"
            :label="caseSingular"
            :placeholder="__('Select {0}', [caseSingular])"
          />
          <p class="text-p-sm text-ink-gray-5">
            {{
              __(
                'Pick a Case first, then attach. Files always stay linked to a Case.',
              )
            }}
          </p>
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="showUpload = false" />
          <Button
            variant="solid"
            :label="__('Continue')"
            :disabled="!uploadDeal"
            @click="continueUpload"
          />
        </div>
      </template>
    </Dialog>

    <FilesUploader
      v-if="uploadDeal"
      v-model="showFilesUploader"
      doctype="CRM Deal"
      :docname="uploadDeal"
      @after="onUploaded"
    />
  </div>
</template>

<script setup>
import FilesUploader from '@/components/FilesUploader/FilesUploader.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import Link from '@/components/Controls/Link.vue'
import { useLifeAgencyMode } from '@/composables/lifeAgency'
import {
  Breadcrumbs,
  Button,
  Dialog,
  LoadingIndicator,
  TextInput,
  createListResource,
} from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { dealsLabel, dealSingular } = useLifeAgencyMode()
const casesLabel = computed(() => dealsLabel.value || __('Deals'))
const caseSingular = computed(() => dealSingular.value || __('Deal'))

const breadcrumbs = computed(() => [
  { label: __('Documents'), route: { name: 'Documents' } },
])

const search = ref('')
const showUpload = ref(false)
const showFilesUploader = ref(false)
const uploadDeal = ref('')

const list = createListResource({
  doctype: 'File',
  fields: [
    'name',
    'file_name',
    'file_url',
    'file_type',
    'file_size',
    'attached_to_doctype',
    'attached_to_name',
    'owner',
    'modified',
    'creation',
  ],
  filters: { attached_to_doctype: 'CRM Deal' },
  orderBy: 'modified desc',
  pageLength: 100,
  auto: true,
  cache: ['InsuranceOps', 'Deal Files'],
})

const rows = computed(() => list.data || [])

const filteredRows = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter((r) => {
    const hay = `${r.file_name || ''} ${r.attached_to_name || ''} ${r.file_type || ''}`.toLowerCase()
    return hay.includes(q)
  })
})

function openUpload() {
  uploadDeal.value = ''
  showUpload.value = true
}

function continueUpload() {
  if (!uploadDeal.value) return
  showUpload.value = false
  showFilesUploader.value = true
}

function onUploaded() {
  list.reload()
  showFilesUploader.value = false
}

function openFile(row) {
  if (row?.file_url) {
    window.open(row.file_url, '_blank')
  }
}

function openCase(row) {
  if (!row?.attached_to_name) return
  router.push({
    name: 'Deal',
    params: { dealId: row.attached_to_name },
    hash: '#attachments',
  })
}

function formatSize(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}
</script>
