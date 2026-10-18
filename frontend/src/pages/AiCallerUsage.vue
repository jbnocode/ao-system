<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Button
          variant="subtle"
          :label="__('Assignments')"
          @click="openAssignments"
        />
        <Button
          variant="subtle"
          icon-left="lucide-refresh-cw"
          :label="__('Refresh')"
          :loading="usage.loading"
          @click="reload"
        />
      </template>
    </LayoutHeader>

    <div class="min-h-0 flex-1 overflow-y-auto bg-surface-white px-5 py-5">
      <div class="mb-5 flex flex-wrap items-end gap-3">
        <div>
          <label class="mb-1.5 block text-xs text-ink-gray-5">{{
            __('Period')
          }}</label>
          <FormControl
            v-model="days"
            type="select"
            class="w-40"
            :options="dayOptions"
          />
        </div>
        <div class="min-w-[220px]">
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
      </div>

      <div v-if="usage.loading && !usage.data" class="flex justify-center py-16">
        <LoadingIndicator class="w-4" />
      </div>
      <template v-else-if="usage.data">
        <div class="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div
            v-for="card in summaryCards"
            :key="card.label"
            class="rounded-5 border border-outline-gray-modals px-4 py-3"
          >
            <div class="text-p-sm text-ink-gray-5">{{ card.label }}</div>
            <div class="mt-1 text-xl font-semibold text-ink-gray-9">
              {{ card.value }}
            </div>
          </div>
        </div>

        <div class="mb-2 text-p-base-medium text-ink-gray-8">
          {{ __('By agent') }}
        </div>
        <div
          v-if="!usage.data.agents?.length"
          class="mb-8 rounded-5 border border-outline-gray-modals px-4 py-8 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No AI caller agents assigned yet.') }}
        </div>
        <div v-else class="mb-8 flex flex-col">
          <div
            v-for="row in usage.data.agents"
            :key="row.user"
            class="flex flex-col gap-1 border-b border-outline-gray-modals py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div class="min-w-0">
              <div class="text-p-base-medium text-ink-gray-8">
                {{ row.user_name }}
              </div>
              <div class="text-p-sm text-ink-gray-5">
                {{ row.phone_number || __('No number') }}
                <span v-if="!row.setup_completed">
                  · {{ __('Setup pending') }}</span
                >
              </div>
            </div>
            <div
              class="flex flex-wrap gap-3 text-p-sm text-ink-gray-7 sm:justify-end"
            >
              <span>{{ __('{0} calls', [row.calls]) }}</span>
              <span>{{ __('{0} min', [row.minutes]) }}</span>
              <span>${{ row.cost.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <div class="mb-2 text-p-base-medium text-ink-gray-8">
          {{ __('Recent calls') }}
        </div>
        <div
          v-if="!usage.data.recent?.length"
          class="rounded-5 border border-outline-gray-modals px-4 py-8 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No calls in this period.') }}
        </div>
        <div v-else class="flex flex-col">
          <div
            v-for="row in usage.data.recent"
            :key="row.id"
            class="flex flex-col gap-1 border-b border-outline-gray-modals py-3 sm:flex-row sm:items-start sm:justify-between"
          >
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-p-base-medium text-ink-gray-8">
                  {{ row.user_name || __('Unknown') }}
                </span>
                <Badge
                  :label="row.status || __('—')"
                  variant="subtle"
                  :theme="statusTheme(row.status)"
                />
                <span v-if="row.type" class="text-p-sm text-ink-gray-5">
                  {{ row.type }}
                </span>
              </div>
              <div class="mt-0.5 text-p-sm text-ink-gray-5">
                <span v-if="row.customer">{{ row.customer }} · </span>
                {{ formatWhen(row.created_at) }}
              </div>
            </div>
            <div class="shrink-0 text-p-sm text-ink-gray-7">
              {{ formatDuration(row.seconds) }}
              <span v-if="row.cost"> · ${{ Number(row.cost).toFixed(3) }}</span>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="py-8 text-p-sm text-ink-gray-5">
        {{ __('Could not load usage.') }}
      </div>
    </div>
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import {
  activeSettingsPage,
  showSettings,
} from '@/composables/settings'
import { formatDate } from '@/utils'
import {
  Badge,
  Breadcrumbs,
  Button,
  FormControl,
  LoadingIndicator,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const breadcrumbs = [
  { label: __('AI Caller'), route: { name: 'AI Caller Usage' } },
]

const days = ref('30')
const userFilter = ref('')

const dayOptions = [
  { label: __('Last 7 days'), value: '7' },
  { label: __('Last 30 days'), value: '30' },
  { label: __('Last 90 days'), value: '90' },
]

const usage = createResource({
  url: 'crm.vapi.api.get_usage_dashboard',
  makeParams: () => ({
    days: days.value,
    user: userFilter.value || undefined,
  }),
  auto: true,
  onError(err) {
    toast.error(
      err?.messages?.[0] || err?.message || __('Could not load AI caller usage'),
    )
  },
})

const summaryCards = computed(() => {
  const t = usage.data?.totals || {}
  return [
    { label: __('Calls'), value: t.calls ?? 0 },
    { label: __('Ended'), value: t.ended ?? 0 },
    { label: __('Failed'), value: t.failed ?? 0 },
    { label: __('Minutes'), value: t.minutes ?? 0 },
    {
      label: __('Est. cost'),
      value: `$${Number(t.cost || 0).toFixed(2)}`,
    },
  ]
})

watch(days, () => reload())

function reload() {
  usage.reload()
}

function onUserFilter(v) {
  userFilter.value = v || ''
  reload()
}

function clearFilter() {
  userFilter.value = ''
  reload()
}

function openAssignments() {
  activeSettingsPage.value = __('AI Caller')
  showSettings.value = true
}

function statusTheme(status) {
  const s = (status || '').toLowerCase()
  if (s === 'ended') return 'green'
  if (s === 'in-progress' || s === 'ringing' || s === 'queued') return 'blue'
  if (s.includes('fail') || s === 'not-found') return 'red'
  return 'gray'
}

function formatWhen(iso) {
  if (!iso) return ''
  return formatDate(iso, '', true, true)
}

function formatDuration(seconds) {
  const s = Number(seconds) || 0
  if (s < 60) return __('{0}s', [s])
  const m = Math.floor(s / 60)
  const rem = s % 60
  return rem ? __('{0}m {1}s', [m, rem]) : __('{0}m', [m])
}
</script>
