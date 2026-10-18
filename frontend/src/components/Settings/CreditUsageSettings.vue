<template>
  <div class="flex h-full flex-col overflow-y-auto p-8 text-ink-gray-8">
    <h2 class="mb-1 text-2xl-semibold">{{ __('Usage') }}</h2>
    <p class="mb-6 text-p-base text-ink-gray-6">
      {{ __('Credit spend history across agents.') }}
    </p>

    <div class="mb-4 flex max-w-2xl flex-wrap items-end gap-3">
      <div class="min-w-[220px] flex-1">
        <label class="mb-1.5 block text-xs text-ink-gray-5">{{
          __('Agent')
        }}</label>
        <Link
          :model-value="userFilter"
          doctype="User"
          :placeholder="__('All agents')"
          @update:model-value="onUserFilter"
        />
      </div>
      <Button
        v-if="userFilter"
        variant="subtle"
        :label="__('Clear')"
        @click="clearFilter"
      />
      <Button
        variant="subtle"
        icon-left="lucide-refresh-cw"
        :label="__('Refresh')"
        :loading="logs.loading"
        @click="reload"
      />
    </div>

    <div v-if="logs.loading && !logs.data?.length" class="flex justify-center py-12">
      <LoadingIndicator class="w-4" />
    </div>
    <div v-else-if="!logs.data?.length" class="text-p-sm text-ink-gray-5 py-4">
      {{ __('No usage yet.') }}
    </div>
    <div v-else class="max-w-3xl flex flex-col">
      <div
        v-for="row in logs.data"
        :key="row.name"
        class="flex flex-col gap-1 border-b border-outline-gray-modals py-3 sm:flex-row sm:items-start sm:justify-between"
      >
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-p-base-medium text-ink-gray-8">
              {{ row.user_name }}
            </span>
            <Badge
              :label="row.status || __('—')"
              variant="subtle"
              :theme="statusTheme(row.status)"
            />
            <span
              v-if="row.context_type"
              class="text-p-sm text-ink-gray-5"
            >
              {{ row.context_type }}
            </span>
          </div>
          <div
            v-if="row.message_preview"
            class="mt-0.5 text-p-sm text-ink-gray-5 truncate"
          >
            {{ row.message_preview }}
          </div>
          <div class="mt-0.5 text-p-sm text-ink-gray-4">
            {{ formatDate(row.creation, '', true, true) }}
          </div>
        </div>
        <div class="shrink-0 text-p-base-medium text-ink-gray-8">
          −{{ row.credits_spent }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import {
  activeSettingsPage,
  creditUsageUserFilter,
} from '@/composables/settings'
import { formatDate } from '@/utils'
import {
  Badge,
  Button,
  LoadingIndicator,
  createResource,
  toast,
} from 'frappe-ui'
import { onMounted, ref, watch } from 'vue'

const userFilter = ref(creditUsageUserFilter.value || '')

const logs = createResource({
  url: 'crm.ai.credits.list_credit_usage',
  makeParams: () => ({
    user: userFilter.value || undefined,
    limit: 50,
  }),
  onError: (err) => {
    err?.messages?.forEach((msg) => toast.error(msg))
  },
})

function reload() {
  logs.fetch()
}

function onUserFilter(value) {
  userFilter.value = value || ''
  creditUsageUserFilter.value = userFilter.value
  reload()
}

function clearFilter() {
  userFilter.value = ''
  creditUsageUserFilter.value = ''
  reload()
}

function statusTheme(status) {
  if (status === 'Success') return 'green'
  if (status === 'Failed') return 'red'
  if (status === 'Demo') return 'orange'
  return 'gray'
}

onMounted(() => {
  userFilter.value = creditUsageUserFilter.value || ''
  reload()
})

watch(activeSettingsPage, (page) => {
  if (page === 'Usage') {
    userFilter.value = creditUsageUserFilter.value || ''
    reload()
  }
})
</script>
