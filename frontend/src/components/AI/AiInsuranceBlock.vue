<template>
  <div class="mt-3 space-y-2">
    <div
      v-if="block.title"
      class="flex items-center justify-between gap-2 text-p-sm-medium text-ink-gray-7"
    >
      <span>{{ block.title }}</span>
      <Badge
        v-if="kindLabel"
        :label="kindLabel"
        theme="gray"
        variant="subtle"
      />
    </div>
    <div class="flex flex-col gap-2">
      <div
        v-for="(item, i) in block.items || []"
        :key="item.name || i"
        class="rounded-lg border border-outline-gray-modals bg-surface-white p-3"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="text-base font-medium text-ink-gray-9">
              {{ item.carrier || __('No carrier') }}
              <span v-if="item.product" class="text-ink-gray-5">
                - {{ item.product }}
              </span>
            </div>
            <div class="mt-0.5 text-p-sm text-ink-gray-5">
              <template v-if="item.name">{{ item.name }}</template>
              <template v-if="item.policy_number">
                <span v-if="item.name"> · </span>{{ item.policy_number }}
              </template>
              <template v-if="item.term_years">
                <span v-if="item.name || item.policy_number"> · </span>
                {{ __('Term') }}: {{ item.term_years }}
              </template>
              <template v-if="item.deal">
                <span
                  v-if="item.name || item.policy_number || item.term_years"
                >
                  ·
                </span>
                {{ item.deal }}
              </template>
            </div>
          </div>
          <Badge
            v-if="item.status"
            :label="item.status"
            :theme="statusTheme(item.status)"
            variant="subtle"
          />
        </div>
        <div class="mt-2 flex flex-wrap gap-6 text-p-sm text-ink-gray-7">
          <div>
            <div class="text-ink-gray-5">{{ __('Face amount') }}</div>
            <div class="font-medium">{{ money(item.face_amount) }}</div>
          </div>
          <div>
            <div class="text-ink-gray-5">{{ __('Monthly premium') }}</div>
            <div class="font-medium">{{ money(item.monthly_premium) }}</div>
          </div>
        </div>
        <div v-if="item.deal" class="mt-2">
          <Button
            size="sm"
            variant="subtle"
            :label="openLabel"
            @click="openOnDeal(item)"
          />
        </div>
      </div>
    </div>
    <p
      v-if="block.kind === 'Catalog'"
      class="text-p-sm text-ink-gray-5"
    >
      {{
        __(
          'Indicative catalog only. Open a Case → Quotes to save options on a deal.',
        )
      }}
    </p>
  </div>
</template>

<script setup>
import { Badge, Button } from 'frappe-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  block: { type: Object, required: true },
})

const router = useRouter()

const kindLabel = computed(() => {
  if (props.block.kind === 'Policies') return __('Policies')
  if (props.block.kind === 'Quotes') return __('Quotes')
  if (props.block.kind === 'Catalog') return __('Catalog')
  return ''
})

const openLabel = computed(() => {
  if (props.block.kind === 'Policies' || props.block.tab === 'policies') {
    return __('Open on case')
  }
  return __('Open on case')
})

function openOnDeal(item) {
  if (!item?.deal) return
  const hash = props.block.tab === 'policies' ? 'policies' : 'quotes'
  router.push({
    name: 'Deal',
    params: { dealId: item.deal },
    hash: `#${hash}`,
  })
}

function money(v) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(Number(v) || 0)
}

function statusTheme(s) {
  if (['Accepted', 'Approved', 'Issued', 'In Force'].includes(s)) return 'green'
  if (['Declined', 'Lapsed', 'Cancelled'].includes(s)) return 'red'
  if (['Presented', 'Submitted', 'Underwriting', 'Indicative'].includes(s))
    return 'blue'
  return 'gray'
}
</script>
