<template>
  <div class="flex h-full min-h-0 bg-surface-white">
    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <!-- Single top bar -->
      <div
        class="flex h-14 shrink-0 items-center gap-3 border-b border-outline-gray-2 px-3"
      >
        <div class="flex min-w-0 flex-1 items-center gap-2">
          <Button
            variant="ghost"
            icon="lucide-arrow-left"
            :aria-label="__('Back')"
            @click="$emit('close')"
          />
          <div class="min-w-0 shrink" @focus="selectTitle">
            <div
              class="title-sizer font-semibold text-ink-gray-8"
              :data-value="doc.title || __('Untitled automation')"
            >
              <TextInput
                variant="ghost"
                :model-value="doc.title"
                :aria-label="__('Automation title')"
                :placeholder="__('Untitled automation')"
                @update:model-value="setTitle"
              />
            </div>
          </div>
          <span
            v-if="dirty || !automationName"
            class="shrink-0 text-p-sm text-ink-gray-5"
          >
            {{ __('Not saved yet') }}
          </span>
        </div>

        <TabButtons v-model="tab" :options="tabOptions" />

        <div class="flex flex-1 items-center justify-end gap-2">
          <Button
            :label="__('Save')"
            variant="solid"
            :loading="saving"
            :disabled="!dirty"
            @click="saveAutomation"
          />
          <div
            class="flex items-center gap-2 border-l border-outline-gray-2 pl-2"
          >
            <span class="text-p-sm text-ink-gray-6">
              {{ doc.enabled ? __('Published') : __('Draft') }}
            </span>
            <Switch
              size="sm"
              :model-value="Boolean(doc.enabled)"
              :disabled="!doc.trigger_type"
              :aria-label="__('Published')"
              @update:model-value="doc.enabled = $event ? 1 : 0"
            />
          </div>
        </div>
      </div>

      <div v-if="tab === 'test'" class="min-h-0 flex-1 overflow-y-auto p-4">
        <AutomationTrialRun
          v-if="canTest"
          :automation-name="automationName"
          :doc="doc"
        />
        <p v-else class="text-p-sm text-ink-gray-5">
          {{ __('Save the flow before testing it.') }}
        </p>
      </div>
      <div
        v-else
        class="relative min-h-0 flex-1 bg-surface-gray-1 outline-none"
        autofocus
        tabindex="0"
      >
        <WorkflowFlow
          :nodes="nodes"
          :edges="edges"
          :block-groups="blocks"
          :trigger-groups="triggers"
          :selected-id="selectedId"
          :dim-unselected="showInspector"
          :can-delete="canDeleteSelected"
          :can-undo="canUndo"
          :can-redo="canRedo"
          @select="selectNode"
          @add-step="addStep"
          @pick-trigger="pickTrigger"
          @request-remove="confirmSelectedRemoval"
          @undo="undo"
          @redo="redo"
        />
        <div class="absolute right-3 top-3 z-10 flex items-center gap-2">
          <Button
            class="shadow-sm transition-transform active:scale-95"
            variant="subtle"
            :aria-label="
              aiOpen ? __('Close AI Builder') : __('Open AI Builder')
            "
            :aria-pressed="aiOpen"
            @click="aiOpen = !aiOpen"
          >
            <template #icon>
              <AiBuilderIcon class="size-4" />
            </template>
          </Button>
          <Button
            v-if="doc.trigger_type"
            class="shadow-sm transition-transform active:scale-95"
            variant="subtle"
            :aria-label="
              inspectorOpen ? __('Close inspector') : __('Open inspector')
            "
            :aria-expanded="inspectorOpen"
            @click="inspectorOpen = !inspectorOpen"
          >
            <template #icon>
              <CollapseIcon
                class="size-4 transition-transform duration-200 ease-out"
                :class="{ 'rotate-180': inspectorOpen }"
              />
            </template>
          </Button>
        </div>
      </div>
    </div>

    <div
      class="min-h-0 shrink-0 overflow-hidden border-l border-outline-gray-2 transition-[width] duration-200 ease-out motion-reduce:transition-none"
      :class="showAi ? 'w-[320px]' : 'w-0'"
      :aria-hidden="!showAi"
      :inert="!showAi"
    >
      <div class="h-full w-[320px] overflow-hidden bg-surface-white">
        <AutomationAiChat :snapshot="aiSnapshot" @apply="onApplyAi" />
      </div>
    </div>

    <div
      class="min-h-0 shrink-0 overflow-hidden border-l border-outline-gray-2 transition-[width] duration-200 ease-out motion-reduce:transition-none"
      :class="showInspector ? 'w-[340px]' : 'w-0'"
      :aria-hidden="!showInspector"
      :inert="!showInspector"
    >
      <div class="h-full w-[340px] overflow-hidden bg-surface-white">
        <AutomationInspector
          :doc="doc"
          :selected-step="selectedStep"
          :targets="targetsFor(selectedStep)"
          :loading="loading"
          @update="patchDoc"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import AutomationInspector from './WorkflowAutomationInspector.vue'
import AutomationTrialRun from './WorkflowTrialRun.vue'
import AutomationAiChat from './AutomationAiChat.vue'
import WorkflowFlow from './WorkflowFlow.vue'
import { useKeyboardShortcuts } from '@/composables/useKeyboardShortcuts'
import { useUndoHistory } from '@/composables/useUndoHistory'
import { applyAiOps } from '@/utils/applyAiOps'
import { globalStore } from '@/stores/global'
import { blockGroups } from './workflowBlocks'
import { aliasTargets, loadCapabilities } from './workflowCapabilities'
import { workflowEdges, workflowNodes } from './workflowGraph'
import { triggerFromValue, triggerGroups } from './workflowTriggers'
import { firstBlockingRow, hasValues, triggerIssue } from './workflowValidation'
import {
  adoptRowKeys,
  insertAfter,
  layoutSteps,
  newStep,
  nodeAtRow,
  removeStep,
  stepsBefore,
  toRows,
  toTree,
} from './workflowSteps'
import { Button, Switch, TabButtons, TextInput, call, toast } from 'frappe-ui'
import AiBuilderIcon from '~icons/lucide/wand-sparkles'
import CollapseIcon from '~icons/lucide/chevrons-left'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  automationName: { type: String, default: '' },
})

const emit = defineEmits(['close', 'saved', 'update:dirty'])
const { $dialog } = globalStore()

const loading = ref(false)
const saving = ref(false)
const tab = ref('editor')
/** Closed until a non-trigger step is selected (or user opens it). */
const inspectorOpen = ref(false)
/** Closed by default; user opens via AI Builder. */
const aiOpen = ref(false)
const selectedId = ref('trigger')
const errors = reactive({})
const doc = reactive(defaultDoc())
const savedSnapshot = ref('')

const tabOptions = [
  { label: __('Builder'), value: 'editor' },
  { label: __('Test'), value: 'test' },
]

const placed = computed(() => layoutSteps(doc.actions))

const selectedStep = computed(() => {
  return (
    placed.value.find((item) => item.node._id === selectedId.value)?.node ||
    null
  )
})

const nodes = computed(() => workflowNodes(doc, errors))
const edges = computed(() => workflowEdges(doc.actions))
const blocks = computed(() => blockGroups(doc.document_type))
const triggers = computed(() => triggerGroups(doc.document_type))

const relationships = computed(() => parseJson(doc.relationships, []))

/** Every alias a step can target, outputs of steps the flow gained included. */
const flowTargets = computed(() =>
  aliasTargets(doc.document_type, relationships.value, toRows(doc.actions)),
)
/** Kept mounted while hidden so the panel can slide out instead of vanishing. */
const showInspector = computed(
  () => tab.value === 'editor' && inspectorOpen.value,
)
const showAi = computed(() => tab.value === 'editor' && aiOpen.value)
const canDeleteSelected = computed(() =>
  selectedId.value === 'trigger'
    ? Boolean(doc.trigger_type)
    : Boolean(selectedStep.value),
)

const {
  canUndo,
  canRedo,
  undo,
  redo,
  flush: flushHistory,
  reset: resetHistory,
  absorb: absorbHistory,
} = useUndoHistory(doc, applySnapshot, { ignore: ['enabled'] })

useKeyboardShortcuts({
  shortcuts: [
    {
      keys: ['Backspace', 'Delete'],
      guard: () => canDeleteSelected.value,
      action: confirmSelectedRemoval,
    },
    { match: isUndoKey, action: undo },
    { match: isRedoKey, action: redo },
  ],
})

/** Compared against the last loaded/saved state so closing can warn about unsaved edits. */
const dirty = computed(() => savedSnapshot.value !== JSON.stringify(payload()))

/** A trial runs the saved flow, so unsaved edits would not be what gets tested. */
const canTest = computed(() => Boolean(props.automationName) && !dirty.value)

watch(flowTargets, loadTargetCapabilities, { immediate: true, deep: true })
watch(dirty, (value) => emit('update:dirty', value), { immediate: true })

loadAutomation()

function defaultDoc() {
  return {
    doctype: 'Automation Flow',
    title: '',
    document_type: 'CRM Lead',
    enabled: 0,
    trigger_type: '',
    trigger_field: '',
    from_value: '',
    to_value: '',
    custom_event: '',
    date_field: '',
    date_offset: 0,
    date_direction: 'Before',
    cron_expression: '',
    filters: '[]',
    condition: '',
    relationships: '[]',
    run_as: 'Automation User',
    automation_user: '',
    revalidate_on_run: 0,
    actions: [],
    stop_on_error: 1,
    throttle_per_minute: 0,
  }
}

async function loadAutomation() {
  if (!props.automationName) return markClean()
  loading.value = true
  try {
    const saved = await call('frappe.client.get', {
      doctype: 'Automation Flow',
      name: props.automationName,
    })
    Object.assign(doc, saved, {
      actions: toTree((saved.actions || []).map(normalizeRow)),
    })
  } finally {
    loading.value = false
    markClean()
    resetHistory()
  }
}

function markClean() {
  savedSnapshot.value = JSON.stringify(payload())
}

/** Take the server's name, timestamps and step keys, so the next save is not a stale write. */
function adoptSaved(saved) {
  doc.name = saved.name
  doc.creation = saved.creation
  doc.owner = saved.owner
  doc.modified = saved.modified
  adoptRowKeys(doc.actions, saved.actions || [])
  markClean()
  absorbHistory()
}

function setTitle(title) {
  doc.title = title
}

/** Focus lands on the inner input, so select from the wrapper the icon shares. */
function selectTitle(event) {
  if (event.target instanceof HTMLInputElement) event.target.select()
}

function normalizeRow(row) {
  return {
    ...row,
    step_type: row.step_type || 'Action',
    params: stringify(row.params),
    related_condition: stringify(row.related_condition, ''),
  }
}

function stringify(value, fallback = '{}') {
  if (!value) return fallback
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
}

function parseJson(value, fallback) {
  if (!value) return fallback
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

/** Load capabilities for the trigger DocType and every alias a step can target. */
function loadTargetCapabilities() {
  flowTargets.value.forEach((target) => loadCapabilities(target.doctype))
}

function targetsFor(step) {
  if (!step) return []
  return aliasTargets(
    doc.document_type,
    relationships.value,
    stepsBefore(doc.actions, step),
  )
}

function addStep({ after, branch, values }) {
  const created = newStep(values)
  if (!after) doc.actions.push(created)
  else if (branch) after.children[branch].push(created)
  else insertAfter(doc.actions, after, created)
  selectedId.value = created._id
  inspectorOpen.value = true
}

/** The inspector reports its edits rather than writing into the document it is shown. */
function patchDoc(values) {
  Object.assign(doc, values)
}

/** Compact tree for the LLM — ids stay so ops can target steps. */
function aiSnapshot() {
  return {
    title: doc.title,
    document_type: doc.document_type,
    enabled: doc.enabled,
    trigger_type: doc.trigger_type,
    trigger_field: doc.trigger_field,
    from_value: doc.from_value,
    to_value: doc.to_value,
    custom_event: doc.custom_event,
    cron_expression: doc.cron_expression,
    date_field: doc.date_field,
    actions: summarizeActions(doc.actions),
  }
}

function summarizeActions(nodes) {
  return (nodes || []).map((node) => ({
    _id: node._id,
    step_type: node.step_type,
    action_type: node.action_type,
    params: node.params,
    children: node.children
      ? {
          If: summarizeActions(node.children.If),
          Else: summarizeActions(node.children.Else),
        }
      : undefined,
  }))
}

function onApplyAi(ops) {
  const touched = applyAiOps(doc, ops)
  if (touched.length) selectedId.value = touched[touched.length - 1]
  else if (doc.trigger_type) selectedId.value = 'trigger'
  inspectorOpen.value = true
  toast.success(__('Applied to canvas'))
}

/** Restoring replaces the whole document, so the canvas rebuilds from the snapshot. */
function applySnapshot(snapshot) {
  Object.assign(doc, snapshot)
  clearErrors()
  keepSelectionValid()
}

/** A step back can remove the selected step; the trigger is always there to fall back on. */
function keepSelectionValid() {
  if (selectedId.value === 'trigger') return
  if (placed.value.some((item) => item.node._id === selectedId.value)) return
  selectedId.value = 'trigger'
}

function isUndoKey(event) {
  return withModifier(event) && !event.shiftKey && isKey(event, 'z')
}

function isRedoKey(event) {
  if (!withModifier(event)) return false
  return isKey(event, 'y') || (event.shiftKey && isKey(event, 'z'))
}

function withModifier(event) {
  return event.metaKey || event.ctrlKey
}

function isKey(event, key) {
  return event.key.toLowerCase() === key
}

function selectNode(id) {
  selectedId.value = id
  // Open inspector for steps; trigger config stays quieter unless the user opens it.
  if (id !== 'trigger') inspectorOpen.value = true
}

function pickTrigger(trigger) {
  applyTrigger(trigger)
  selectedId.value = 'trigger'
}

/** Event triggers store as a Custom Event; anything else clears the event it replaces. */
function applyTrigger(value) {
  Object.assign(doc, triggerFromValue(value))
}

function removeSelectedStep() {
  if (!selectedStep.value) return
  if (!removeStep(doc.actions, selectedStep.value)) return
  selectedId.value = 'trigger'
}

function confirmSelectedRemoval() {
  if (!canDeleteSelected.value) return
  const deletingTrigger = selectedId.value === 'trigger'
  $dialog({
    title: deletingTrigger ? __('Delete trigger') : __('Delete step'),
    size: 'sm',
    message: deleteMessage(deletingTrigger),
    actions: [{ label: 'Cancel' }, deleteAction(deletingTrigger)],
  })
}

function deleteMessage(deletingTrigger) {
  return deletingTrigger
    ? __('Are you sure you want to delete the trigger and all workflow steps?')
    : __('Are you sure you want to delete this step?')
}

function deleteAction(deletingTrigger) {
  return {
    label: __('Delete'),
    variant: 'solid',
    theme: 'red',
    onClick: ({ close }) => {
      if (deletingTrigger) resetTrigger()
      else removeSelectedStep()
      close()
    },
  }
}

function resetTrigger() {
  Object.assign(doc, emptyTriggerState())
  selectedId.value = 'trigger'
  inspectorOpen.value = false
}

function emptyTriggerState() {
  return {
    trigger_type: '',
    trigger_field: '',
    from_value: '',
    to_value: '',
    custom_event: '',
    date_field: '',
    date_offset: 0,
    date_direction: 'Before',
    cron_expression: '',
    filters: '[]',
    condition: '',
    relationships: '[]',
    actions: [],
  }
}

async function saveAutomation() {
  flushHistory()
  saving.value = true
  clearErrors()
  try {
    validateBeforeSave()
    const saved = props.automationName
      ? await call('frappe.client.save', { doc: payload() })
      : await call('frappe.client.insert', { doc: payload() })
    adoptSaved(saved)
    toast.success(__('Automation saved'))
    emit('saved', saved)
  } catch (error) {
    toast.error(attachError(error))
  } finally {
    saving.value = false
  }
}

function validateBeforeSave() {
  const trigger = triggerIssue(doc)
  if (trigger) throw new Error(trigger)
  const blocking = firstBlockingRow(doc.actions)
  if (!blocking) return
  attachRowError(blocking.row.idx, blocking.issue)
  throw new Error(blocking.issue)
}

function payload() {
  return {
    ...doc,
    title: doc.title || __('Untitled automation'),
    filters: normalizedJsonString(doc.filters, []),
    relationships: JSON.stringify(normalizedRelationships()),
    actions: toRows(doc.actions).map(rowPayload),
  }
}

function normalizedRelationships() {
  return Array.isArray(relationships.value) ? relationships.value : []
}

function normalizedJsonString(value, fallback) {
  return JSON.stringify(parseJson(value, fallback))
}

function rowPayload(row) {
  return {
    ...row,
    doctype: 'Automation Action',
    params: JSON.stringify(normalizedParams(row)),
    related_condition: normalizedRelatedCondition(row.related_condition),
  }
}

function normalizedParams(row) {
  const params = parseJson(row.params, {})
  if (row.action_type !== 'SetFieldValue') return params
  if (!hasValues(params.values)) delete params.values
  return params
}

function normalizedRelatedCondition(value) {
  const condition = parseJson(value, null)
  if (!condition || Array.isArray(condition) || !condition.relationship)
    return null
  return JSON.stringify(condition)
}

function clearErrors() {
  Object.keys(errors).forEach((key) => delete errors[key])
}

/** Server errors read "Row 3: ..." - that points the error at its node, and the node being
    marked is what tells the user where it is, so the prefix leaves the message. */
function attachError(error) {
  const raw = errorMessage(error)
  const match = raw.match(/^Row (\d+):\s*/)
  const message = match ? raw.slice(match[0].length) : raw
  if (match) attachRowError(Number(match[1]), message)
  else if (selectedStep.value) errors[selectedStep.value._id] = [{ message }]
  return message
}

function attachRowError(rowIndex, message) {
  const node = nodeAtRow(doc.actions, rowIndex)
  if (!node) return
  errors[node._id] = [{ message }]
  selectedId.value = node._id
}

function errorMessage(error) {
  const messages = error?.messages || error?._server_messages
  if (Array.isArray(messages) && messages.length)
    return cleanMessage(messages[0])
  return cleanMessage(error?.message || error)
}

function cleanMessage(message) {
  try {
    return JSON.parse(message).message || String(message)
  } catch {
    return String(message || __('Could not save automation'))
  }
}
</script>

<style scoped>
/* An invisible mirror of the text sets the track width, so the field is only
   ever as wide as its content until it hits the cap and truncates. */
.title-sizer {
  display: inline-grid;
  min-width: 0;
  max-width: min(20rem, 40vw);
}

.title-sizer::after,
.title-sizer > * {
  grid-area: 1 / 1;
  min-width: 0;
}

/* Same font and padding as TextInput's sm field so the mirror measures exactly the text. */
.title-sizer::after {
  @apply text-base;
  content: attr(data-value);
  visibility: hidden;
  white-space: pre;
  padding: 0 0.5rem;
}

/* Zero intrinsic width so only the mirror sizes the track; the input then fills it. */
.title-sizer :deep(input) {
  width: 0;
  min-width: 100%;
  cursor: text;
  background: transparent;
  text-overflow: ellipsis;
}

.title-sizer :deep(input::selection) {
  background: var(--surface-gray-3, #e2e8f0);
}
</style>
