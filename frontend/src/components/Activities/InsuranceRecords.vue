<template>
  <div class="px-3 pb-6 sm:px-10">
    <div class="mb-3 flex items-center justify-between">
      <div class="text-p-sm text-ink-gray-6">
        {{ rows.length }} {{ rows.length == 1 ? 'record' : 'records' }}
      </div>
      <Button variant="solid" iconLeft="lucide-plus" :label="__('New')" @click="openNew" />
    </div>
    <div
      v-if="!rows.length && !list.loading"
      class="flex flex-col items-center justify-center gap-2 py-16 text-ink-gray-4"
    >
      <div class="text-lg font-medium">No {{ kind.toLowerCase() }} yet</div>
      <div class="text-p-sm">Add one for this deal with the New button.</div>
    </div>
    <div class="flex flex-col gap-3">
      <div
        v-for="r in rows"
        :key="r.name"
        class="rounded-lg border border-outline-gray-modals bg-surface-white p-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-base font-medium text-ink-gray-9">
              {{ r.carrier || 'No carrier' }}
              <span v-if="r.product" class="text-ink-gray-5">- {{ r.product }}</span>
            </div>
            <div class="mt-1 text-p-sm text-ink-gray-5">
              {{ r.name }}<span v-if="dateOf(r)"> - {{ dateOf(r) }}</span>
              <span v-if="extraOf(r)"> - {{ extraOf(r) }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <Badge :label="r.status" :theme="theme(r.status)" />
            <FormControl
              type="select"
              class="w-32"
              :modelValue="r.status"
              :options="cfg.statuses"
              @update:modelValue="(v) => setStatus(r, v)"
            />
          </div>
        </div>
        <div class="mt-3 flex gap-8 text-p-sm text-ink-gray-7">
          <div>
            <div class="text-ink-gray-5">Face amount</div>
            <div class="font-medium">{{ money(r.face_amount) }}</div>
          </div>
          <div>
            <div class="text-ink-gray-5">Monthly premium</div>
            <div class="font-medium">{{ money(r.monthly_premium) }}</div>
          </div>
        </div>
        <div v-if="convertLabel(r)" class="mt-3">
          <Button
            size="sm"
            variant="subtle"
            :label="convertLabel(r)"
            :loading="converting === r.name"
            @click="convert(r)"
          />
        </div>
      </div>
    </div>
    <Dialog v-model:open="show" :title="__('New') + ' ' + cfg.singular" @close="show = false">
      <template #default>
        <div class="flex flex-col gap-3">
          <FormControl type="text" :label="__('Carrier')" v-model="form.carrier" />
          <FormControl type="text" :label="__('Product')" v-model="form.product" />
          <div class="grid grid-cols-2 gap-3">
            <FormControl type="number" :label="__('Face amount')" v-model="form.face_amount" />
            <FormControl type="number" :label="__('Monthly premium')" v-model="form.monthly_premium" />
          </div>
          <FormControl type="select" :label="__('Status')" :options="cfg.statuses" v-model="form.status" />
          <FormControl type="date" :label="cfg.dateLabel" v-model="form.date" />
          <FormControl :type="cfg.extraType" :label="cfg.extraLabel" v-model="form.extra" />
        </div>
      </template>
      <template #actions>
        <div class="flex items-center justify-between gap-2">
          <div><ErrorMessage :message="error" /></div>
          <div class="flex gap-2">
            <Button :label="__('Cancel')" @click="show = false" />
            <Button variant="solid" :loading="saving" :label="__('Create')" @click="create" />
          </div>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { Badge, Button, Dialog, ErrorMessage, FormControl, call, createListResource, toast } from 'frappe-ui'
import { statusesStore } from '@/stores/statuses'

const props = defineProps({
  deal: { type: String, required: true },
  kind: { type: String, required: true },
})

const emit = defineEmits(['journey-updated'])

const { dealStatuses } = statusesStore()

const KINDS = {
  Quotes: {
    doctype: 'Insurance Quote',
    singular: 'Quote',
    statuses: ['Draft', 'Presented', 'Accepted', 'Declined'],
    dateField: 'quote_date',
    dateLabel: 'Quote date',
    extraField: 'term_years',
    extraLabel: 'Term (years)',
    extraType: 'number',
  },
  Applications: {
    doctype: 'Insurance Application',
    singular: 'Application',
    statuses: ['Draft', 'Submitted', 'Underwriting', 'Approved', 'Declined', 'Issued'],
    dateField: 'submitted_on',
    dateLabel: 'Submitted on',
    extraField: 'underwriting_class',
    extraLabel: 'Underwriting class',
    extraType: 'text',
  },
  Policies: {
    doctype: 'Insurance Policy',
    singular: 'Policy',
    statuses: ['Pending', 'In Force', 'Lapsed', 'Cancelled'],
    dateField: 'effective_date',
    dateLabel: 'Effective date',
    extraField: 'policy_number',
    extraLabel: 'Policy number',
    extraType: 'text',
  },
}
const cfg = computed(() => KINDS[props.kind])

const list = createListResource({
  doctype: KINDS[props.kind].doctype,
  fields: ['name', 'carrier', 'product', 'face_amount', 'monthly_premium', 'status', KINDS[props.kind].dateField, KINDS[props.kind].extraField],
  filters: { deal: props.deal },
  orderBy: 'modified desc',
  pageLength: 50,
  auto: true,
})
const rows = computed(() => list.data || [])

const show = ref(false)
const saving = ref(false)
const converting = ref('')
const error = ref('')
const form = reactive({ carrier: '', product: '', face_amount: '', monthly_premium: '', status: '', date: '', extra: '' })

function openNew() {
  Object.assign(form, { carrier: '', product: '', face_amount: '', monthly_premium: '', status: cfg.value.statuses[0], date: '', extra: '' })
  error.value = ''
  show.value = true
}

async function create() {
  saving.value = true
  error.value = ''
  try {
    const doc = {
      doctype: cfg.value.doctype,
      deal: props.deal,
      carrier: form.carrier,
      product: form.product,
      face_amount: form.face_amount || 0,
      monthly_premium: form.monthly_premium || 0,
      status: form.status,
    }
    if (form.date) doc[cfg.value.dateField] = form.date
    if (form.extra !== '' && form.extra !== null) doc[cfg.value.extraField] = form.extra
    await call('frappe.client.insert', { doc })
    show.value = false
    list.reload()
    toast.success(cfg.value.singular + ' created')
    maybeSuggestDealStatus(form.status)
    emit('journey-updated')
  } catch (e) {
    error.value = e?.messages?.join(' ') || e?.message || 'Could not save'
  } finally {
    saving.value = false
  }
}

async function setStatus(r, value) {
  if (value === r.status) return
  try {
    await call('frappe.client.set_value', { doctype: cfg.value.doctype, name: r.name, fieldname: 'status', value })
    list.reload()
    maybeSuggestDealStatus(value)
    emit('journey-updated')
  } catch (e) {
    toast.error('Could not change status')
  }
}

function convertLabel(r) {
  if (props.kind === 'Quotes' && ['Presented', 'Accepted', 'Draft'].includes(r.status)) {
    return __('Create application')
  }
  if (props.kind === 'Applications' && ['Approved', 'Issued', 'Underwriting'].includes(r.status)) {
    return __('Create policy')
  }
  return ''
}

async function convert(r) {
  converting.value = r.name
  try {
    if (props.kind === 'Quotes') {
      const res = await call('crm.life.api.convert_quote_to_application', { quote: r.name })
      toast.success(__('Application {0} created', [res.application]))
      if (res.deal_status) {
        toast.info(__('Deal moved to {0}', [res.deal_status]))
        dealStatuses.reload()
      }
    } else if (props.kind === 'Applications') {
      const res = await call('crm.life.api.convert_application_to_policy', {
        application: r.name,
      })
      toast.success(__('Policy {0} created', [res.policy]))
      if (res.deal_status) {
        toast.info(__('Deal moved to {0}', [res.deal_status]))
        dealStatuses.reload()
      }
    }
    list.reload()
    emit('journey-updated')
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Could not convert'))
  } finally {
    converting.value = ''
  }
}

const STATUS_HINTS = {
  Quotes: { Presented: 'Quoted', Accepted: 'Application Submitted' },
  Applications: {
    Submitted: 'Application Submitted',
    Underwriting: 'Underwriting',
    Approved: 'Approved',
    Issued: 'Policy Delivered',
    Declined: 'Declined',
  },
  Policies: {
    Pending: 'Approved',
    'In Force': 'Policy Delivered',
  },
}

function maybeSuggestDealStatus(recordStatus) {
  const suggested = STATUS_HINTS[props.kind]?.[recordStatus]
  if (!suggested) return
  toast.info(__('Suggested deal stage: {0} (use Life journey strip to apply)', [suggested]))
}

function dateOf(r) {
  return r[cfg.value.dateField] || ''
}
function extraOf(r) {
  const v = r[cfg.value.extraField]
  return v ? cfg.value.extraLabel + ': ' + v : ''
}
function money(v) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v || 0)
}
function theme(s) {
  if (['Accepted', 'Approved', 'Issued', 'In Force'].includes(s)) return 'green'
  if (['Declined', 'Lapsed', 'Cancelled'].includes(s)) return 'red'
  if (['Presented', 'Submitted', 'Underwriting'].includes(s)) return 'blue'
  return 'gray'
}
</script>
