<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <div class="flex items-center gap-2">
          <Button
            variant="subtle"
            :label="__('Ask AI')"
            @click="router.push({ name: 'AI' })"
          />
          <Button
            variant="subtle"
            :label="__('Open {0}', [casesLabel])"
            @click="router.push({ name: 'Deals' })"
          />
        </div>
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-white">
      <div
        class="flex flex-wrap items-center gap-3 border-b border-outline-gray-modals px-4 py-3"
      >
        <TabButtons v-model="kind" :options="tabOptions" />
        <FormControl
          v-model="statusFilter"
          type="select"
          size="sm"
          class="w-40"
          :options="statusOptions"
        />
        <p class="text-p-sm text-ink-gray-5">
          {{ tabHint }}
        </p>
        <div class="ml-auto">
          <Button
            size="sm"
            variant="ghost"
            icon="lucide-refresh-cw"
            :aria-label="__('Refresh')"
            :loading="activeList.loading"
            @click="activeList.reload()"
          />
        </div>
      </div>

      <div class="min-h-0 flex-1 overflow-y-auto">
        <div
          v-if="activeList.loading && !rows.length"
          class="flex justify-center py-16"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div
          v-else-if="!rows.length"
          class="px-4 py-12 text-center text-p-sm text-ink-gray-5"
        >
          {{ emptyCopy }}
          <div class="mt-3 flex justify-center gap-2">
            <Button
              variant="solid"
              size="sm"
              :label="__('Go to {0}', [casesLabel])"
              @click="router.push({ name: 'Deals' })"
            />
            <Button
              v-if="kind === 'quotes'"
              variant="subtle"
              size="sm"
              :label="__('Ask AI')"
              @click="router.push({ name: 'AI' })"
            />
          </div>
        </div>
        <div v-else class="divide-y divide-outline-gray-modals">
          <button
            v-for="row in filteredRows"
            :key="row.name"
            type="button"
            class="flex w-full items-start gap-4 px-4 py-3 text-left transition hover:bg-surface-gray-1"
            @click="openRow(row)"
          >
            <div class="min-w-0 flex-1">
              <div class="text-p-base-medium text-ink-gray-9">
                {{ row.carrier || __('No carrier') }}
                <span v-if="row.product" class="font-normal text-ink-gray-5">
                  · {{ row.product }}
                </span>
              </div>
              <div class="mt-0.5 text-p-sm text-ink-gray-5">
                {{ row.name }}
                <template v-if="row.deal"> · {{ row.deal }}</template>
                <template v-if="row.term_years">
                  · {{ __('Term') }} {{ row.term_years }}
                </template>
              </div>
            </div>
            <div class="shrink-0 text-right text-p-sm text-ink-gray-7">
              <div class="font-medium">
                {{ formatInsuranceMoney(row.face_amount) }}
              </div>
              <div class="text-ink-gray-5">
                {{ formatInsuranceMoney(row.monthly_premium) }}/mo
              </div>
            </div>
            <Badge
              class="shrink-0"
              :label="row.status"
              :theme="insuranceStatusTheme(row.status)"
              variant="subtle"
            />
          </button>
        </div>
        <div
          v-if="filteredRows.length === 0 && rows.length"
          class="px-4 py-10 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No records match this filter.') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import { useLifeAgencyMode } from '@/composables/lifeAgency'
import {
  formatInsuranceMoney,
  insuranceStatusTheme,
} from '@/utils/insuranceFormat'
import {
  Badge,
  Breadcrumbs,
  Button,
  FormControl,
  LoadingIndicator,
  TabButtons,
  createListResource,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()
const { dealsLabel } = useLifeAgencyMode()
const casesLabel = computed(() => dealsLabel.value || __('Deals'))

const breadcrumbs = computed(() => [
  { label: __('Quoting'), route: { name: 'Quoting' } },
])

const tabOptions = [
  { label: __('Quotes'), value: 'quotes' },
  { label: __('Applications'), value: 'applications' },
]

const VALID = new Set(tabOptions.map((t) => t.value))
const kind = ref(
  VALID.has(route.hash?.replace('#', ''))
    ? route.hash.replace('#', '')
    : 'quotes',
)

watch(kind, (value) => {
  statusFilter.value = ''
  const hash = `#${value}`
  if (route.hash !== hash) {
    router.replace({ ...route, hash })
  }
})

watch(
  () => route.hash,
  (hash) => {
    const value = hash?.replace('#', '')
    if (VALID.has(value) && kind.value !== value) {
      kind.value = value
    }
  },
)

const statusFilter = ref('')

const quoteStatuses = [
  { label: __('All statuses'), value: '' },
  { label: __('Draft'), value: 'Draft' },
  { label: __('Presented'), value: 'Presented' },
  { label: __('Accepted'), value: 'Accepted' },
  { label: __('Declined'), value: 'Declined' },
]

const appStatuses = [
  { label: __('All statuses'), value: '' },
  { label: __('Draft'), value: 'Draft' },
  { label: __('Submitted'), value: 'Submitted' },
  { label: __('Underwriting'), value: 'Underwriting' },
  { label: __('Approved'), value: 'Approved' },
  { label: __('Declined'), value: 'Declined' },
  { label: __('Issued'), value: 'Issued' },
]

const statusOptions = computed(() =>
  kind.value === 'applications' ? appStatuses : quoteStatuses,
)

const quotes = createListResource({
  doctype: 'Insurance Quote',
  fields: [
    'name',
    'deal',
    'status',
    'carrier',
    'product',
    'face_amount',
    'monthly_premium',
    'term_years',
    'quote_date',
    'modified',
  ],
  orderBy: 'modified desc',
  pageLength: 100,
  auto: true,
  cache: ['InsuranceOps', 'Insurance Quote'],
})

const applications = createListResource({
  doctype: 'Insurance Application',
  fields: [
    'name',
    'deal',
    'status',
    'carrier',
    'product',
    'face_amount',
    'monthly_premium',
    'submitted_on',
    'modified',
  ],
  orderBy: 'modified desc',
  pageLength: 100,
  auto: true,
  cache: ['InsuranceOps', 'Insurance Application'],
})

const lists = { quotes, applications }
const activeList = computed(() => lists[kind.value] || quotes)
const rows = computed(() => activeList.value.data || [])

const filteredRows = computed(() => {
  if (!statusFilter.value) return rows.value
  return rows.value.filter((r) => r.status === statusFilter.value)
})

const tabHint = computed(() =>
  kind.value === 'applications'
    ? __('Submitted apps waiting on underwriting or issue.')
    : __('Options presented on cases. Accept a quote to move toward an application.'),
)

const emptyCopy = computed(() =>
  kind.value === 'applications'
    ? __(
        'No applications yet. Accept a quote on a Case, then create an application.',
      )
    : __(
        'No quotes yet. Open a Case and add options, or ask AI for indicative quotes.',
      ),
)

function openRow(row) {
  if (!row?.deal) {
    router.push({ name: 'Deals' })
    return
  }
  router.push({
    name: 'Deal',
    params: { dealId: row.deal },
    hash: kind.value === 'applications' ? '#applications' : '#quotes',
  })
}
</script>
