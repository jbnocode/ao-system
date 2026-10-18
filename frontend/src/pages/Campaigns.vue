<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Dropdown :options="createMenuOptions">
          <Button
            :label="__('New')"
            variant="solid"
            icon-left="lucide-plus"
            icon-right="lucide-chevron-down"
          />
        </Dropdown>
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 overflow-hidden bg-surface-white">
      <!-- Campaign list -->
      <div
        class="flex min-h-0 w-full flex-col border-r border-outline-gray-modals lg:w-96 lg:shrink-0"
        :class="selected ? 'hidden lg:flex' : 'flex'"
      >
        <div class="border-b border-outline-gray-modals px-3 py-3">
          <TextInput
            v-model="search"
            type="text"
            size="sm"
            :placeholder="__('Search campaigns')"
            :debounce="200"
          >
            <template #prefix>
              <LucideSearch class="size-4 text-ink-gray-5" />
            </template>
          </TextInput>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-2 pb-4 pt-1">
          <div
            v-if="campaigns.list.loading && !campaigns.data?.length"
            class="flex justify-center py-12"
          >
            <LoadingIndicator class="w-4" />
          </div>
          <div
            v-else-if="!filtered.length"
            class="px-2 py-10 text-center text-p-sm text-ink-gray-5"
          >
            {{
              __(
                'No campaigns yet. Create a Campaign with Email/SMS schedules, then start Email Campaigns for recipients.',
              )
            }}
          </div>
          <button
            v-for="row in filtered"
            :key="row.name"
            type="button"
            class="flex w-full items-start gap-3 rounded-4 px-2 py-2.5 text-left transition hover:bg-surface-gray-1"
            :class="
              selected === row.name
                ? 'bg-surface-white shadow-sm ring-1 ring-outline-gray-modals'
                : undefined
            "
            @click="selectCampaign(row.name)"
          >
            <div class="min-w-0 flex-1">
              <div class="truncate text-p-base-medium text-ink-gray-8">
                {{ row.campaign_name || row.name }}
              </div>
              <div class="mt-0.5 truncate text-p-sm text-ink-gray-5">
                {{ row.name }}
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Detail -->
      <div
        class="flex min-h-0 min-w-0 flex-1 flex-col"
        :class="!selected ? 'hidden lg:flex' : 'flex'"
      >
        <div
          v-if="!selected"
          class="flex flex-1 items-center justify-center text-p-sm text-ink-gray-5"
        >
          {{ __('Select a campaign') }}
        </div>
        <template v-else-if="detail.loading && !detail.data">
          <div class="flex flex-1 items-center justify-center">
            <LoadingIndicator class="w-4" />
          </div>
        </template>
        <template v-else-if="detail.data">
          <div
            class="flex items-center gap-2 border-b border-outline-gray-modals px-4 py-2.5"
          >
            <Button
              class="lg:hidden"
              icon="lucide-arrow-left"
              variant="ghost"
              @click="selected = ''"
            />
            <div class="min-w-0 flex-1">
              <div class="truncate text-base font-medium text-ink-gray-9">
                {{ detail.data.campaign_name }}
              </div>
              <div class="text-p-sm text-ink-gray-5">{{ detail.data.name }}</div>
            </div>
            <Button
              :label="__('View Leads')"
              variant="subtle"
              @click="openLeads"
            />
            <Button
              :label="__('New Email Campaign')"
              variant="solid"
              icon-left="lucide-plus"
              @click="openEnroll"
            />
            <Button icon="lucide-pencil" variant="ghost" @click="openEdit" />
          </div>

          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6">
            <div
              v-if="detail.data.description"
              class="mb-6 text-p-sm text-ink-gray-7"
            >
              {{ detail.data.description }}
            </div>

            <div class="mb-2 text-p-sm font-medium text-ink-gray-8">
              {{ __('Campaign Schedules') }}
            </div>
            <div
              v-if="!(detail.data.campaign_schedules || []).length"
              class="mb-6 text-p-sm text-ink-gray-5"
            >
              {{
                __(
                  'No schedules yet. Edit the campaign to add Email Template or SMS rows (Send After days).',
                )
              }}
            </div>
            <div v-else class="mb-8 flex flex-col gap-2">
              <div
                v-for="(step, i) in detail.data.campaign_schedules"
                :key="step.name || i"
                class="flex items-center justify-between gap-3 rounded-4 border border-outline-gray-modals px-3 py-2 text-p-sm"
              >
                <div class="min-w-0">
                  <Badge
                    :label="step.channel || 'Email'"
                    :theme="step.channel === 'SMS' ? 'green' : 'blue'"
                    variant="outline"
                  />
                  <span class="ml-2 text-ink-gray-5">
                    {{ __('Send After {0} day(s)', [step.send_after_days]) }}
                  </span>
                  <div class="mt-0.5 truncate text-ink-gray-8">
                    {{
                      step.channel === 'SMS'
                        ? step.sms_body
                        : step.email_template
                    }}
                  </div>
                </div>
              </div>
            </div>

            <div class="mb-2 flex items-center justify-between">
              <div class="text-p-sm font-medium text-ink-gray-8">
                {{ __('Email Campaigns') }}
                <span class="font-normal text-ink-gray-5">
                  ({{ (detail.data.email_campaigns || []).length }})
                </span>
              </div>
            </div>
            <div
              v-if="!(detail.data.email_campaigns || []).length"
              class="text-p-sm text-ink-gray-5"
            >
              {{
                __(
                  'No Email Campaigns yet. Enroll a CRM Lead, Contact, Case/Deal, or Email Group to start the schedule.',
                )
              }}
            </div>
            <div v-else class="flex flex-col gap-1">
              <div
                v-for="ec in detail.data.email_campaigns"
                :key="ec.name"
                class="flex items-center justify-between gap-2 rounded-4 px-2 py-1.5 text-p-sm hover:bg-surface-gray-1"
              >
                <div class="min-w-0 truncate">
                  <span class="text-ink-gray-5">{{
                    ec.email_campaign_for
                  }}</span>
                  ·
                  <span class="text-ink-gray-8">{{ ec.recipient }}</span>
                  <span class="text-ink-gray-5">
                    · {{ ec.start_date }}
                    <template v-if="ec.end_date"
                      >→ {{ ec.end_date }}</template
                    >
                  </span>
                </div>
                <Badge
                  :label="ec.status || __('—')"
                  :theme="ecStatusTheme(ec.status)"
                  variant="outline"
                />
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Create / Edit Campaign definition -->
    <Dialog
      v-model:open="showForm"
      :title="editingName ? __('Edit campaign') : __('New campaign')"
      size="xl"
    >
      <template #default>
        <div class="flex flex-col gap-3">
          <FormControl
            v-model="form.campaign_name"
            type="text"
            :label="__('Campaign name')"
            required
          />
          <FormControl
            v-model="form.description"
            type="textarea"
            :label="__('Description')"
          />

          <div class="mt-2 flex items-center justify-between">
            <div class="text-p-sm font-medium text-ink-gray-8">
              {{ __('Campaign Schedules') }}
            </div>
            <Button
              size="sm"
              variant="subtle"
              icon-left="lucide-plus"
              :label="__('Add row')"
              @click="addSchedule"
            />
          </div>
          <div
            v-for="(step, i) in form.campaign_schedules"
            :key="i"
            class="rounded-4 border border-outline-gray-modals p-3"
          >
            <div class="mb-2 flex items-center justify-between">
              <div class="text-p-sm text-ink-gray-5">
                {{ __('Schedule {0}', [i + 1]) }}
              </div>
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-trash-2"
                @click="form.campaign_schedules.splice(i, 1)"
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <FormControl
                v-model="step.channel"
                type="select"
                :label="__('Channel')"
                :options="stepChannelOptions"
              />
              <FormControl
                v-model="step.send_after_days"
                type="number"
                :label="__('Send After (days)')"
              />
            </div>
            <Link
              v-if="step.channel === 'Email'"
              v-model="step.email_template"
              class="mt-3"
              doctype="Email Template"
              :label="__('Email Template')"
              :placeholder="__('Select Email Template')"
              :required="true"
            />
            <FormControl
              v-else
              v-model="step.sms_body"
              class="mt-3"
              type="textarea"
              :label="__('SMS Body')"
              :placeholder="smsBodyPlaceholder"
            />
          </div>
          <ErrorMessage :message="formError" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="showForm = false" />
          <Button
            :label="__('Save')"
            variant="solid"
            :loading="saving"
            @click="saveForm"
          />
        </div>
      </template>
    </Dialog>

    <!-- Templates -->
    <Dialog
      v-model:open="showLibrary"
      :title="__('Campaign templates')"
      size="lg"
    >
      <template #default>
        <div
          v-if="templates.loading && !templates.data"
          class="flex justify-center py-8"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div v-else class="flex flex-col gap-5">
          <div v-for="group in templateGroups" :key="group.label">
            <div class="mb-2 text-sm text-ink-gray-5">{{ group.label }}</div>
            <div class="flex flex-col gap-1.5">
              <button
                v-for="t in group.items"
                :key="t.id"
                type="button"
                class="flex w-full flex-col gap-0.5 rounded-4 border border-outline-gray-2 px-3 py-2.5 text-left transition-colors hover:bg-surface-gray-1 disabled:opacity-50"
                :disabled="creatingFromTemplate"
                @click="useTemplate(t)"
              >
                <span class="text-base-medium text-ink-gray-8">{{
                  t.title
                }}</span>
                <span class="text-p-sm text-ink-gray-5">{{
                  t.description
                }}</span>
              </button>
            </div>
          </div>
        </div>
      </template>
    </Dialog>

    <!-- New Email Campaign (enroll) -->
    <Dialog
      v-model:open="showEnroll"
      :title="__('New Email Campaign')"
      size="lg"
    >
      <template #default>
        <div class="flex flex-col gap-3">
          <FormControl
            v-model="enrollDoctype"
            type="select"
            :label="__('Email Campaign For')"
            :options="recipientTypeOptions"
          />
          <FormControl
            v-model="enrollStart"
            type="date"
            :label="__('Start date')"
          />
          <TextInput
            v-model="enrollSearch"
            type="text"
            size="sm"
            :placeholder="__('Search recipient')"
            :debounce="250"
          />
          <div
            class="max-h-64 overflow-y-auto rounded-4 border border-outline-gray-modals"
          >
            <label
              v-for="row in enrollResults"
              :key="row.name"
              class="flex cursor-pointer items-center gap-2 border-b border-outline-gray-modals px-3 py-2 text-p-sm last:border-0 hover:bg-surface-gray-1"
            >
              <input
                v-model="enrollSelected"
                type="checkbox"
                class="rounded"
                :value="row.name"
              />
              <div class="min-w-0 flex-1 truncate">
                <span class="text-ink-gray-8">{{ row.title || row.name }}</span>
                <span v-if="row.email" class="text-ink-gray-5">
                  · {{ row.email }}
                </span>
              </div>
            </label>
            <div
              v-if="!enrollResults.length"
              class="px-3 py-6 text-center text-p-sm text-ink-gray-5"
            >
              {{ __('No matches') }}
            </div>
          </div>
          <ErrorMessage :message="enrollError" />
        </div>
      </template>
      <template #actions>
        <div class="flex justify-end gap-2">
          <Button :label="__('Cancel')" @click="showEnroll = false" />
          <Button
            :label="__('Create {0}', [enrollSelected.length])"
            variant="solid"
            :loading="enrolling"
            :disabled="!enrollSelected.length"
            @click="enroll"
          />
        </div>
      </template>
    </Dialog>

    <!-- View Leads -->
    <Dialog v-model:open="showLeads" :title="__('Leads')" size="lg">
      <template #default>
        <div
          v-if="leads.loading && !leads.data"
          class="flex justify-center py-8"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div
          v-else-if="!(leads.data || []).length"
          class="py-8 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No leads tagged to this campaign yet.') }}
        </div>
        <div v-else class="flex flex-col gap-1">
          <router-link
            v-for="lead in leads.data"
            :key="lead.name"
            :to="{ name: 'Lead', params: { leadId: lead.name } }"
            class="flex items-center justify-between rounded-4 px-2 py-2 text-p-sm hover:bg-surface-gray-1"
          >
            <span class="text-ink-gray-8">{{
              lead.lead_name || lead.name
            }}</span>
            <span class="text-ink-gray-5">{{ lead.status }}</span>
          </router-link>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import {
  Badge,
  Breadcrumbs,
  Button,
  Dialog,
  Dropdown,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  TextInput,
  call,
  createListResource,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import LucideSearch from '~icons/lucide/search'

const breadcrumbs = [{ label: __('Campaigns'), route: { name: 'Campaigns' } }]
const search = ref('')
const selected = ref('')
const showForm = ref(false)
const showLibrary = ref(false)
const showEnroll = ref(false)
const showLeads = ref(false)
const creatingFromTemplate = ref(false)
const editingName = ref('')
const saving = ref(false)
const formError = ref('')
const enrollDoctype = ref('CRM Lead')
const enrollSearch = ref('')
const enrollStart = ref('')
const enrollResults = ref([])
const enrollSelected = ref([])
const enrolling = ref(false)
const enrollError = ref('')

const stepChannelOptions = [
  { label: __('Email'), value: 'Email' },
  { label: __('SMS'), value: 'SMS' },
]
const smsBodyPlaceholder = __('Hi {{ doc.first_name or "there" }}, …')
const recipientTypeOptions = [
  { label: __('CRM Lead'), value: 'CRM Lead' },
  { label: __('Contact'), value: 'Contact' },
  { label: __('CRM Deal'), value: 'CRM Deal' },
  { label: __('Email Group'), value: 'Email Group' },
]

const form = reactive({
  campaign_name: '',
  description: '',
  campaign_schedules: [],
})

const createMenuOptions = computed(() => [
  {
    group: __('Create'),
    hideLabel: true,
    options: [
      {
        label: __('New campaign'),
        icon: 'lucide-plus',
        onClick: () => openCreate(),
      },
      {
        label: __('Templates'),
        icon: 'lucide-layout-template',
        onClick: () => openTemplateLibrary(),
      },
    ],
  },
])

const campaigns = createListResource({
  doctype: 'CRM Campaign',
  fields: ['name', 'campaign_name', 'description', 'modified'],
  orderBy: 'modified desc',
  pageLength: 50,
  auto: true,
  cache: 'crmCampaigns',
})

const detail = createResource({
  url: 'crm.api.campaign.get_campaign',
  makeParams: () => ({ name: selected.value }),
  auto: false,
})

const templates = createResource({
  url: 'crm.api.campaign_templates.list_campaign_templates',
  auto: false,
  cache: 'crmCampaignTemplates',
})

const leads = createResource({
  url: 'crm.api.campaign.get_leads_for_campaign',
  makeParams: () => ({ campaign: selected.value }),
  auto: false,
})

const templateGroups = computed(() => {
  const rows = templates.data || []
  return [
    { key: 'email', label: __('Email') },
    { key: 'sms', label: __('SMS') },
    { key: 'mixed', label: __('Email + SMS') },
  ]
    .map((g) => ({
      label: g.label,
      items: rows.filter((t) => t.category === g.key),
    }))
    .filter((g) => g.items.length)
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  const rows = campaigns.data || []
  if (!q) return rows
  return rows.filter(
    (r) =>
      (r.campaign_name || '').toLowerCase().includes(q) ||
      (r.name || '').toLowerCase().includes(q),
  )
})

watch(selected, (name) => {
  if (name) detail.reload()
})

watch([enrollDoctype, enrollSearch, showEnroll], async () => {
  if (!showEnroll.value) return
  try {
    enrollResults.value = await call('crm.api.campaign.search_recipients', {
      doctype: enrollDoctype.value,
      txt: enrollSearch.value,
      limit: 30,
    })
  } catch {
    enrollResults.value = []
  }
})

function ecStatusTheme(status) {
  return (
    {
      Scheduled: 'blue',
      'In Progress': 'amber',
      Completed: 'green',
      Unsubscribed: 'gray',
    }[status] || 'gray'
  )
}

function selectCampaign(name) {
  selected.value = name
}

function resetForm() {
  form.campaign_name = ''
  form.description = ''
  form.campaign_schedules = []
  formError.value = ''
  editingName.value = ''
}

function openCreate() {
  resetForm()
  addSchedule()
  showForm.value = true
}

function openEdit() {
  const d = detail.data
  if (!d) return
  editingName.value = d.name
  form.campaign_name = d.campaign_name || ''
  form.description = d.description || ''
  form.campaign_schedules = (d.campaign_schedules || []).map((s) => ({
    channel: s.channel || 'Email',
    send_after_days: s.send_after_days ?? 0,
    email_template: s.email_template || '',
    sms_body: s.sms_body || '',
  }))
  if (!form.campaign_schedules.length) addSchedule()
  formError.value = ''
  showForm.value = true
}

function addSchedule() {
  form.campaign_schedules.push({
    channel: 'Email',
    send_after_days: form.campaign_schedules.length ? 3 : 0,
    email_template: '',
    sms_body: '',
  })
}

function openTemplateLibrary() {
  showLibrary.value = true
  templates.reload()
}

function openEnroll() {
  enrollSelected.value = []
  enrollError.value = ''
  enrollStart.value = new Date().toISOString().slice(0, 10)
  showEnroll.value = true
}

function openLeads() {
  showLeads.value = true
  leads.reload()
}

async function useTemplate(t) {
  creatingFromTemplate.value = true
  try {
    const doc = await call(
      'crm.api.campaign_templates.create_from_template',
      { template_id: t.id },
    )
    toast.success(__('Campaign created from template'))
    showLibrary.value = false
    await campaigns.reload()
    selected.value = doc.name
    await detail.reload()
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not create from template'),
    )
  } finally {
    creatingFromTemplate.value = false
  }
}

async function saveForm() {
  formError.value = ''
  if (!form.campaign_name.trim()) {
    formError.value = __('Campaign name is required')
    return
  }
  for (const s of form.campaign_schedules) {
    if (s.channel === 'Email' && !(s.email_template || '').trim()) {
      formError.value = __('Each Email schedule needs an Email Template')
      return
    }
    if (s.channel === 'SMS' && !(s.sms_body || '').trim()) {
      formError.value = __('Each SMS schedule needs a message body')
      return
    }
  }
  saving.value = true
  try {
    const doc = await call('crm.api.campaign.save_campaign', {
      doc: {
        name: editingName.value || undefined,
        campaign_name: form.campaign_name.trim(),
        description: form.description || '',
        campaign_schedules: form.campaign_schedules.map((s) => ({
          channel: s.channel || 'Email',
          send_after_days: Number(s.send_after_days) || 0,
          email_template: s.channel === 'Email' ? s.email_template : '',
          sms_body: s.channel === 'SMS' ? s.sms_body : '',
        })),
      },
    })
    toast.success(__('Campaign saved'))
    showForm.value = false
    await campaigns.reload()
    selected.value = doc.name
    await detail.reload()
  } catch (e) {
    formError.value =
      e?.messages?.[0] || e?.message || __('Could not save campaign')
  } finally {
    saving.value = false
  }
}

async function enroll() {
  enrollError.value = ''
  enrolling.value = true
  try {
    const res = await call('crm.api.campaign.enroll_members', {
      campaign: selected.value,
      reference_doctype: enrollDoctype.value,
      names: enrollSelected.value,
      start_date: enrollStart.value || undefined,
    })
    const msg =
      res.errors?.length && res.added
        ? __('Created {0}; {1} failed', [res.added, res.errors.length])
        : __('Created {0} Email Campaign(s)', [res.added])
    toast.success(msg)
    if (res.errors?.length && !res.added) {
      enrollError.value = res.errors.join('\n')
      return
    }
    showEnroll.value = false
    enrollSelected.value = []
    await detail.reload()
  } catch (e) {
    enrollError.value =
      e?.messages?.[0] || e?.message || __('Could not create Email Campaign')
  } finally {
    enrolling.value = false
  }
}
</script>
