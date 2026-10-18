<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Button
          variant="subtle"
          :label="__('Open {0}', [casesLabel])"
          @click="router.push({ name: 'Deals' })"
        />
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-white">
      <div
        class="flex flex-wrap items-center gap-2 border-b border-outline-gray-modals px-4 py-3"
      >
        <FormControl
          v-model="statusFilter"
          type="select"
          size="sm"
          class="w-40"
          :options="statusOptions"
        />
        <div class="flex flex-wrap gap-2 text-p-sm text-ink-gray-6">
          <span
            v-for="chip in statusChips"
            :key="chip.status"
            class="text-ink-gray-5"
          >
            <span class="font-medium text-ink-gray-8">{{ chip.count }}</span>
            {{ chip.status }}
          </span>
        </div>
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
              'No policies yet. When coverage is issued, add a policy on the Case.',
            )
          }}
          <div class="mt-3">
            <Button
              variant="solid"
              size="sm"
              :label="__('Go to {0}', [casesLabel])"
              @click="router.push({ name: 'Deals' })"
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
                <template v-if="row.policy_number">
                  · {{ row.policy_number }}
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
          {{ __('No policies match this filter.') }}
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
  createListResource,
} from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const { dealsLabel } = useLifeAgencyMode()
const casesLabel = computed(() => dealsLabel.value || __('Deals'))

const breadcrumbs = computed(() => [
  { label: __('Policies'), route: { name: 'Policies' } },
])

const statusFilter = ref('')
const statusOptions = [
  { label: __('All statuses'), value: '' },
  { label: __('Pending'), value: 'Pending' },
  { label: __('In Force'), value: 'In Force' },
  { label: __('Lapsed'), value: 'Lapsed' },
  { label: __('Cancelled'), value: 'Cancelled' },
]

const list = createListResource({
  doctype: 'Insurance Policy',
  fields: [
    'name',
    'deal',
    'status',
    'carrier',
    'product',
    'face_amount',
    'monthly_premium',
    'policy_number',
    'effective_date',
    'modified',
  ],
  orderBy: 'modified desc',
  pageLength: 100,
  auto: true,
  cache: ['InsuranceOps', 'Insurance Policy'],
})

const rows = computed(() => list.data || [])

const filteredRows = computed(() => {
  if (!statusFilter.value) return rows.value
  return rows.value.filter((r) => r.status === statusFilter.value)
})

const statusChips = computed(() => {
  const counts = {}
  for (const r of rows.value) {
    counts[r.status] = (counts[r.status] || 0) + 1
  }
  return ['In Force', 'Pending', 'Lapsed', 'Cancelled']
    .filter((s) => counts[s])
    .map((status) => ({ status, count: counts[status] }))
})

function openRow(row) {
  if (!row?.deal) {
    router.push({ name: 'Deals' })
    return
  }
  router.push({
    name: 'Deal',
    params: { dealId: row.deal },
    hash: '#policies',
  })
}
</script>
