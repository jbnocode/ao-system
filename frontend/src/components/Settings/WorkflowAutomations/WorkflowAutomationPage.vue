<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
  <SettingsLayoutBase
    v-if="screen === 'list'"
    :title="__('Workflow Automations')"
    :description="__('Create workflow automations for CRM documents.')"
    :hide-header="asPage"
  >
    <template v-if="!asPage" #title>
      <div class="flex items-center gap-2">
        <h2 class="flex text-2xl-semibold leading-tight">
          {{ __('Workflow Automations') }}
        </h2>
        <Tooltip :text="__('View documentation')">
          <a
            href="https://docs.frappe.io/wiki-app/spaces/22qcan55rk/page/36r50jmgu2"
            target="_blank"
          >
            <LucideCircleQuestionMark class="h-4 w-4 text-ink-gray-6" />
          </a>
        </Tooltip>
      </div>
    </template>
    <template v-if="!asPage" #header-actions>
      <Dropdown :options="createMenuOptions">
        <Button
          :label="__('New')"
          variant="solid"
          icon-left="lucide-plus"
          icon-right="lucide-chevron-down"
        />
      </Dropdown>
    </template>
    <template #header-bottom>
      <div class="flex flex-wrap items-center gap-2 pb-4">
        <TabButtons v-model="statusFilter" :options="statusFilterOptions" />

        <Dropdown :options="agentFilterOptions">
          <Button
            variant="subtle"
            icon-left="lucide-users"
            icon-right="lucide-chevron-down"
            :label="agentFilterLabel"
          />
        </Dropdown>

        <div class="relative min-w-[160px] flex-1 max-w-xs">
          <TextInput
            v-model="search"
            :placeholder="__('Search...')"
            :debounce="300"
            class="rounded-4 border-outline-gray-2 bg-surface-gray-2"
          >
            <template #prefix>
              <span class="lucide-search size-4" aria-hidden="true" />
            </template>
          </TextInput>
          <Button
            v-if="search"
            icon="lucide-x"
            variant="ghost"
            class="absolute right-1 top-1/2 -translate-y-1/2"
            @click="search = ''"
          />
        </div>

        <div class="ml-auto flex flex-wrap items-center gap-1.5">
          <Button
            variant="subtle"
            icon="lucide-clock"
            :tooltip="__('Reload list')"
            @click="reloadList"
          />
          <Button
            variant="subtle"
            icon="lucide-layout-template"
            :tooltip="__('Templates')"
            @click="openTemplateLibrary"
          />
        </div>
      </div>
    </template>
    <template #content>
      <div v-if="automations.list.loading" class="mt-10 flex justify-center">
        <LoadingIndicator class="w-4" />
      </div>
      <EmptyState
        v-else-if="!filteredAutomations.length"
        name="Workflow Automations"
        :icon="WorkflowIcon"
        :title="__('No workflow automations yet')"
        :description="__('Add one to get started.')"
        width="lg"
      />
      <List
        v-else
        class="workflow-automation-list"
        :columns="listColumns"
        :row-height="56"
        divider="full"
      >
        <ListHeader class="sticky top-0 z-10 mx-3 bg-surface-elevation-2">
          <ListHeaderCell>{{ __('Name') }}</ListHeaderCell>
          <ListHeaderCell>{{ __('Document Type') }}</ListHeaderCell>
          <ListHeaderCell>{{ __('Status') }}</ListHeaderCell>
          <ListHeaderCell>{{ __('Enabled') }}</ListHeaderCell>
          <ListHeaderCell>{{ __('Created By') }}</ListHeaderCell>
        </ListHeader>
        <ListRows
          v-slot="{ item: row }"
          :items="filteredAutomations"
          row-key="name"
        >
          <ListRow :value="row.name" @click="openAutomation(row)">
            <ListCell>
              <span class="truncate text-base-medium text-ink-gray-7">
                {{ row.title || row.name }}
              </span>
            </ListCell>
            <ListCell>
              <span class="truncate text-sm">
                {{ row.document_type || __('Any document') }}
              </span>
            </ListCell>

            <ListCell>
              <Badge
                :label="row.enabled ? __('Enabled') : __('Draft')"
                :theme="row.enabled ? 'green' : 'amber'"
                variant="outline"
              />
            </ListCell>
            <ListCell>
              <div @click.stop>
                <Switch
                  size="sm"
                  :model-value="Boolean(row.enabled)"
                  :disabled="toggling.has(row.name)"
                  :aria-label="__('Enabled')"
                  @update:model-value="toggleAutomation(row, $event)"
                />
              </div>
            </ListCell>
            <ListCell>
              <div
                class="flex w-full items-center justify-between pr-1"
                @click.stop
              >
                <Tooltip :text="getUser(row.owner).full_name">
                  <UserAvatar :user="row.owner" size="sm" />
                </Tooltip>
                <Dropdown
                  align="end"
                  :options="rowOptions(row)"
                  @update:open="(open) => open && (confirmingDelete = '')"
                >
                  <Button
                    icon="lucide-more-horizontal"
                    variant="ghost"
                    class="ml-auto"
                  />
                </Dropdown>
              </div>
            </ListCell>
          </ListRow>
        </ListRows>
      </List>
    </template>
  </SettingsLayoutBase>
  <!-- Open straight into the editor (no separate detail/preview screen). -->
  <div v-else class="min-h-0 flex-1">
    <WorkflowAutomationBuilder
      :automation-name="selectedAutomation"
      @update:dirty="dirty = $event"
      @close="requestClose"
      @saved="onSaved"
    />
  </div>

  <Dialog
    v-model:open="showLibrary"
    :title="__('Automation templates')"
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
              <span class="text-p-sm text-ink-gray-5">{{ t.description }}</span>
              <span class="mt-0.5 text-xs text-ink-gray-4">
                {{ t.document_type || __('Any document') }}
                <template v-if="t.trigger_type">
                  · {{ t.trigger_type }}
                </template>
              </span>
            </button>
          </div>
        </div>
        <p
          v-if="!(templates.data || []).length"
          class="py-6 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No templates available.') }}
        </p>
      </div>
    </template>
  </Dialog>
  </div>
</template>

<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import LucideCircleQuestionMark from '~icons/lucide/circle-question-mark'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import WorkflowAutomationBuilder from './WorkflowAutomationBuilder.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import WorkflowIcon from '~icons/lucide/workflow'
import { ConfirmDelete } from '@/utils'
import { createDialog } from '@/utils/dialogs'
import { usersStore } from '@/stores/users'
import {
  List,
  ListCell,
  ListHeader,
  ListHeaderCell,
  ListRow,
  ListRows,
} from 'frappe-ui/list'
import {
  Badge,
  Button,
  Dialog,
  Dropdown,
  LoadingIndicator,
  Switch,
  TabButtons,
  TextInput,
  Tooltip,
  call,
  createListResource,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

defineProps({
  /** Full-page mode: title/New live in LayoutHeader instead of the body. */
  asPage: { type: Boolean, default: false },
})

const { getUser } = usersStore()

const screen = ref('list')
const search = ref('')
const statusFilter = ref('all')
const agentFilter = ref('')
const selectedAutomation = ref('')
const confirmingDelete = ref('')
const dirty = ref(false)
const showLibrary = ref(false)
const creatingFromTemplate = ref(false)
const toggling = reactive(new Set())

const templates = createResource({
  url: 'crm.api.automation_templates.list_automation_templates',
  auto: true,
  cache: 'crmAutomationTemplates',
})

const templateGroups = computed(() => {
  const list = templates.data || []
  const groups = []
  const general = list.filter((t) => t.category === 'general')
  const insurance = list.filter((t) => t.category === 'insurance')
  if (general.length) {
    groups.push({ label: __('General'), items: general })
  }
  if (insurance.length) {
    groups.push({ label: __('Insurance'), items: insurance })
  }
  return groups
})

const createMenuOptions = computed(() => [
  {
    group: __('Create'),
    hideLabel: true,
    options: [
      {
        label: __('New automation'),
        icon: 'lucide-plus',
        onClick: () => newAutomation(),
      },
      {
        label: __('Templates'),
        icon: 'lucide-layout-template',
        onClick: () => openTemplateLibrary(),
      },
    ],
  },
])
const listColumns = [
  'minmax(0, 4fr)',
  'minmax(0, 2fr)',
  'minmax(0, 1.3fr)',
  'minmax(0, 1fr)',
  'minmax(0, 1.5fr)',
]

const automations = createListResource({
  doctype: 'Automation Flow',
  fields: [
    'name',
    'title',
    'document_type',
    'owner',
    'enabled',
    'creation',
    'modified',
  ],
  cache: ['workflowAutomations'],
  orderBy: 'creation desc',
  pageLength: 99,
  auto: true,
})

const allRows = computed(() => automations.data || [])

const statusCounts = computed(() => {
  const rows = allRows.value
  return {
    all: rows.length,
    active: rows.filter((r) => r.enabled).length,
    inactive: rows.filter((r) => !r.enabled).length,
  }
})

const statusFilterOptions = computed(() => [
  { label: __('All ({0})', [statusCounts.value.all]), value: 'all' },
  { label: __('Active ({0})', [statusCounts.value.active]), value: 'active' },
  {
    label: __('Inactive ({0})', [statusCounts.value.inactive]),
    value: 'inactive',
  },
])

const agentFilterLabel = computed(() => {
  if (!agentFilter.value) return __('All Agents')
  return getUser(agentFilter.value).full_name || agentFilter.value
})

const agentFilterOptions = computed(() => {
  const owners = [
    ...new Set(allRows.value.map((r) => r.owner).filter(Boolean)),
  ]
  return [
    {
      group: __('Filter by agent'),
      hideLabel: true,
      options: [
        {
          label: __('All Agents'),
          icon: 'lucide-users',
          onClick: () => {
            agentFilter.value = ''
          },
        },
        ...owners.map((email) => ({
          label: getUser(email).full_name || email,
          icon: 'lucide-user',
          onClick: () => {
            agentFilter.value = email
          },
        })),
      ],
    },
  ]
})

const filteredAutomations = computed(() => {
  let rows = allRows.value
  if (statusFilter.value === 'active') {
    rows = rows.filter((row) => row.enabled)
  } else if (statusFilter.value === 'inactive') {
    rows = rows.filter((row) => !row.enabled)
  }
  if (agentFilter.value) {
    rows = rows.filter((row) => row.owner === agentFilter.value)
  }
  if (search.value) {
    rows = rows.filter((row) => matchesSearch(row))
  }
  return sortByNewestCreated(rows)
})

function matchesSearch(row) {
  const query = search.value.toLowerCase()
  return [row.title, row.name, row.document_type, getUser(row.owner).full_name]
    .filter(Boolean)
    .some((value) => value.toLowerCase().includes(query))
}

function sortByNewestCreated(rows) {
  return [...rows].sort(compareCreatedDesc)
}

function compareCreatedDesc(a, b) {
  return compareDesc(a.creation, b.creation) || compareDesc(a.name, b.name)
}

function compareDesc(a, b) {
  return String(b || '').localeCompare(String(a || ''))
}

function newAutomation() {
  selectedAutomation.value = ''
  screen.value = 'builder'
}

function openTemplateLibrary() {
  showLibrary.value = true
  if (!templates.data) templates.reload()
}

async function useTemplate(t) {
  if (creatingFromTemplate.value) return
  creatingFromTemplate.value = true
  try {
    const doc = await call(
      'crm.api.automation_templates.create_from_template',
      { template_id: t.id },
    )
    showLibrary.value = false
    toast.success(__('Automation created from template'))
    reloadList()
    selectedAutomation.value = doc.name
    screen.value = 'builder'
  } catch (error) {
    toast.error(
      error?.messages?.[0] ||
        error?.message ||
        __('Could not create automation from template'),
    )
  } finally {
    creatingFromTemplate.value = false
  }
}

function openAutomation(automation) {
  selectedAutomation.value = automation.name
  screen.value = 'builder'
}

/** Closing the editor warns first about unsaved edits, then returns to the list. */
function requestClose() {
  if (!dirty.value) return closeBuilder()
  createDialog({
    title: __('Unsaved changes'),
    message: __('You have unsaved changes. Do you wish to exit?'),
    size: 'sm',
    actions: [
      { label: __('Keep editing'), onClick: ({ close }) => close() },
      {
        label: __('Discard and exit'),
        variant: 'solid',
        theme: 'red',
        onClick: closeBuilder,
      },
    ],
  })
}

function closeBuilder({ close } = {}) {
  close?.()
  dirty.value = false
  backToList()
}

function backToList() {
  selectedAutomation.value = ''
  screen.value = 'list'
  reloadList()
}

function onSaved(saved) {
  selectedAutomation.value = saved?.name || selectedAutomation.value
  reloadList()
}

function reloadList() {
  automations.reload()
}

async function toggleAutomation(automation, enabled) {
  if (toggling.has(automation.name)) return
  const previous = automation.enabled
  automation.enabled = enabled ? 1 : 0
  toggling.add(automation.name)
  try {
    await updateEnabled(automation)
    toast.success(__('Automation updated'))
  } catch (error) {
    automation.enabled = previous
    toast.error(error?.message || __('Could not update automation'))
  } finally {
    toggling.delete(automation.name)
  }
}

function updateEnabled(automation) {
  return call('frappe.client.set_value', {
    doctype: 'Automation Flow',
    name: automation.name,
    fieldname: 'enabled',
    value: automation.enabled,
  })
}

function rowOptions(automation) {
  return [
    {
      label: __('Duplicate'),
      icon: 'lucide-copy',
      onClick: () => duplicateAutomation(automation),
    },
    ...ConfirmDelete({
      isConfirmingDelete: computed({
        get: () => confirmingDelete.value === automation.name,
        set: (value) => (confirmingDelete.value = value ? automation.name : ''),
      }),
      onConfirmDelete: () => deleteAutomation(automation),
    }),
  ]
}

async function duplicateAutomation(automation) {
  try {
    const source = await call('frappe.client.get', {
      doctype: 'Automation Flow',
      name: automation.name,
    })
    await call('frappe.client.insert', { doc: copyOf(source) })
    toast.success(__('Automation duplicated'))
    reloadList()
  } catch (error) {
    toast.error(error.messages?.[0] || __('Could not duplicate automation'))
  }
}

/** A copy starts disabled, so a half-reviewed flow never runs the moment it is saved. */
function copyOf(source) {
  return {
    ...withoutIdentity(source),
    doctype: 'Automation Flow',
    title: nextCopyTitle(source.title),
    enabled: 0,
    actions: (source.actions || []).map(withoutIdentity),
  }
}

const IDENTITY_FIELDS = [
  'name',
  'creation',
  'modified',
  'owner',
  'modified_by',
  'idx',
  'parent',
  'parentfield',
  'parenttype',
]

function withoutIdentity(row) {
  const copy = { ...row }
  IDENTITY_FIELDS.forEach((field) => delete copy[field])
  return copy
}

/** "Welcome lead sequence" -> "Welcome lead sequence (1)", skipping names already taken. */
function nextCopyTitle(title) {
  const taken = new Set((automations.data || []).map((row) => row.title))
  let index = 1
  while (taken.has(`${title} (${index})`)) index += 1
  return `${title} (${index})`
}

async function deleteAutomation(automation) {
  await call('frappe.client.delete', {
    doctype: 'Automation Flow',
    name: automation.name,
  })
  toast.success(__('Automation deleted'))
  confirmingDelete.value = ''
  reloadList()
}

defineExpose({
  newAutomation,
  openTemplateLibrary,
  createMenuOptions,
  screen,
})
</script>

<style scoped>
/* Match the header's rule so rows read as one table. */
.workflow-automation-list :deep([data-slot='list-divider']) {
  border-color: var(--outline-gray-2);
}
</style>
