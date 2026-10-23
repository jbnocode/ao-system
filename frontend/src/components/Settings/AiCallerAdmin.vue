<template>
  <div class="flex h-full flex-col overflow-y-auto p-8 text-ink-gray-8">
    <div class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h2 class="mb-1 text-2xl-semibold">{{ __('AI Caller') }}</h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Manage Vapi phone numbers from CRM: display name, inbound assistant, webhook, fallback, and agent assignment. Enable Vapi under Settings → Vapi first.',
            )
          }}
        </p>
      </div>
      <div class="flex shrink-0 flex-wrap items-center justify-end gap-2">
        <Button
          variant="subtle"
          :label="__('Usage dashboard')"
          @click="openUsage"
        />
        <Button
          variant="subtle"
          :label="__('Buy Vapi number')"
          @click="openBuy"
        />
        <Button
          variant="subtle"
          icon-left="lucide-refresh-cw"
          :label="__('Refresh')"
          :loading="vapiNumbers.loading || assignments.loading"
          @click="reload"
        />
      </div>
    </div>

    <!-- Vapi phone numbers -->
    <div class="mb-2 text-base-semibold text-ink-gray-9">
      {{ __('Vapi phone numbers') }}
    </div>
    <p class="mb-4 text-p-sm text-ink-gray-6">
      {{
        __(
          'Edit inbound routing and webhooks here instead of the Vapi dashboard. Assign a number to a user to place outbound AI calls from Dialer.',
        )
      }}
    </p>

    <div
      v-if="vapiNumbers.loading && !vapiNumbers.data?.length"
      class="flex justify-center py-10"
    >
      <LoadingIndicator class="w-4" />
    </div>
    <div
      v-else-if="vapiError"
      class="mb-6"
    >
      <ErrorMessage :message="vapiError" />
      <p class="mt-2 text-p-sm text-ink-gray-5">
        {{
          __(
            'Turn on Settings → Vapi and save a private API key, then refresh.',
          )
        }}
      </p>
    </div>
    <div
      v-else-if="!vapiNumbers.data?.length"
      class="mb-8 border-b border-outline-gray-modals py-8 text-center text-p-sm text-ink-gray-5"
    >
      {{ __('No Vapi phone numbers yet. Buy one or add a number in the Vapi dashboard.') }}
    </div>
    <div v-else class="mb-8 flex flex-col">
      <div
        v-for="row in vapiNumbers.data"
        :key="row.id"
        class="flex flex-col gap-2 border-b border-outline-gray-modals py-3 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="min-w-0">
          <div class="text-p-base-medium text-ink-gray-8">
            {{ row.phone_number || row.id }}
            <span
              v-if="row.name"
              class="text-p-sm font-normal text-ink-gray-5"
            >
              · {{ row.name }}
            </span>
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{ row.provider || '—' }}
            <span v-if="row.assistant_id">
              · {{ __('Assistant') }} {{ shortId(row.assistant_id) }}
            </span>
            <span v-else-if="row.squad_id">
              · {{ __('Squad') }} {{ shortId(row.squad_id) }}
            </span>
            <span v-else-if="row.workflow_id">
              · {{ __('Workflow') }} {{ shortId(row.workflow_id) }}
            </span>
            <span v-else> · {{ __('No inbound assistant') }}</span>
            <span v-if="row.ai_linked">
              · {{ __('Assigned to') }}
              {{ row.ai_user_name || row.ai_user }}
            </span>
          </div>
        </div>
        <div class="flex shrink-0 flex-wrap gap-2">
          <Button
            size="sm"
            variant="subtle"
            :label="__('Edit')"
            @click="openEdit(row)"
          />
          <Button
            size="sm"
            variant="subtle"
            :label="row.ai_linked ? __('Reassign') : __('Assign')"
            @click="openAssign(row)"
          />
          <Button
            size="sm"
            variant="subtle"
            theme="red"
            :label="__('Release')"
            :loading="releasing === row.id"
            @click="releaseNumber(row)"
          />
        </div>
      </div>
    </div>

    <!-- Assignments -->
    <div class="mb-2 text-base-semibold text-ink-gray-9">
      {{ __('Assignments') }}
    </div>
    <div
      v-if="assignments.loading && !assignments.data?.length"
      class="flex justify-center py-10"
    >
      <LoadingIndicator class="w-4" />
    </div>
    <div
      v-else-if="!assignments.data?.length"
      class="border-b border-outline-gray-modals py-8 text-center text-p-sm text-ink-gray-5"
    >
      {{ __('No AI caller agents yet.') }}
    </div>
    <div v-else class="mb-8 flex flex-col">
      <div
        v-for="row in assignments.data"
        :key="row.name"
        class="flex flex-col gap-2 border-b border-outline-gray-modals py-3 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="min-w-0">
          <div class="text-p-base-medium text-ink-gray-8">
            {{ row.user_name || row.user }}
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{ row.phone_number || __('No number') }}
            <span v-if="row.setup_completed"> · {{ __('Setup done') }}</span>
            <span v-else> · {{ __('Setup pending') }}</span>
          </div>
        </div>
        <Button
          size="sm"
          variant="subtle"
          :label="__('Unassign')"
          :loading="unassigning === row.user"
          @click="unassign(row.user)"
        />
      </div>
    </div>

    <!-- Twilio import (optional) -->
    <div class="mb-2 text-base-semibold text-ink-gray-9">
      {{ __('Import Twilio number') }}
    </div>
    <p class="mb-4 text-p-sm text-ink-gray-6">
      {{
        __(
          'Optional. Import a number you already own on Twilio into Vapi, then assign it.',
        )
      }}
    </p>
    <div class="mb-2 flex max-w-2xl flex-col gap-3 sm:flex-row sm:items-end">
      <div class="min-w-0 flex-1">
        <FormControl
          v-model="twilioLink.phone_number"
          type="select"
          :label="__('Twilio number')"
          :options="twilioNumberOptions"
        />
      </div>
      <div class="min-w-0 flex-1">
        <label class="mb-1.5 block text-xs text-ink-gray-5">{{
          __('Assign to')
        }}</label>
        <Link
          :model-value="twilioLink.user"
          doctype="User"
          @update:model-value="twilioLink.user = $event"
        />
      </div>
      <Button
        variant="solid"
        :label="__('Import & assign')"
        :loading="twilioLinking"
        :disabled="!twilioLink.phone_number || !twilioLink.user"
        @click="importTwilio"
      />
    </div>
    <ErrorMessage v-if="twilioLinkError" class="mb-4" :message="twilioLinkError" />

    <!-- Edit dialog -->
    <Dialog v-model="editOpen" :options="{ title: __('Edit Vapi number') }">
      <template #body-content>
        <div class="space-y-4">
          <p class="text-p-sm text-ink-gray-6">
            {{ editForm.phone_number || editForm.id }}
          </p>
          <FormControl
            v-model="editForm.name"
            type="text"
            :label="__('Display name')"
          />
          <FormControl
            v-model="editForm.assistant_id"
            type="select"
            :label="__('Inbound assistant')"
            :options="assistantOptions"
          />
          <FormControl
            v-model="editForm.squad_id"
            type="select"
            :label="__('Inbound squad (optional)')"
            :options="squadOptions"
          />
          <FormControl
            v-model="editForm.workflow_id"
            type="text"
            :label="__('Inbound workflow id (optional)')"
          />
          <p class="text-p-sm text-ink-gray-5 -mt-2">
            {{
              __(
                'Use assistant, squad, or workflow — not all three. Assistant wins if set.',
              )
            }}
          </p>
          <FormControl
            v-model="editForm.server_url"
            type="text"
            :label="__('Server URL on number')"
          />
          <div class="flex items-center justify-between gap-3">
            <span class="text-p-sm text-ink-gray-6">{{
              __('Use CRM webhook URL')
            }}</span>
            <Switch v-model="editForm.use_crm_webhook" size="sm" />
          </div>
          <FormControl
            v-model="editForm.fallback_number"
            type="text"
            :label="__('Fallback number (E.164)')"
          />
          <ErrorMessage v-if="editError" :message="editError" />
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          class="w-full"
          :label="__('Save')"
          :loading="editSaving"
          @click="saveEdit"
        />
      </template>
    </Dialog>

    <!-- Assign dialog -->
    <Dialog v-model="assignOpen" :options="{ title: __('Assign to agent') }">
      <template #body-content>
        <div class="space-y-4">
          <p class="text-p-sm text-ink-gray-6">
            {{ assignForm.phone_number || assignForm.id }}
          </p>
          <div>
            <label class="mb-1.5 block text-xs text-ink-gray-5">{{
              __('User')
            }}</label>
            <Link
              :model-value="assignForm.user"
              doctype="User"
              @update:model-value="assignForm.user = $event"
            />
          </div>
          <ErrorMessage v-if="assignError" :message="assignError" />
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          class="w-full"
          :label="__('Assign')"
          :loading="assignSaving"
          :disabled="!assignForm.user"
          @click="saveAssign"
        />
      </template>
    </Dialog>

    <!-- Buy dialog -->
    <Dialog v-model="buyOpen" :options="{ title: __('Buy Vapi number') }">
      <template #body-content>
        <div class="space-y-4">
          <FormControl
            v-model="buyForm.name"
            type="text"
            :label="__('Display name')"
          />
          <FormControl
            v-model="buyForm.area_code"
            type="text"
            :label="__('Desired area code (optional)')"
            placeholder="725"
          />
          <FormControl
            v-model="buyForm.assistant_id"
            type="select"
            :label="__('Inbound assistant (optional)')"
            :options="assistantOptions"
          />
          <div>
            <label class="mb-1.5 block text-xs text-ink-gray-5">{{
              __('Assign to (optional)')
            }}</label>
            <Link
              :model-value="buyForm.assign_to"
              doctype="User"
              @update:model-value="buyForm.assign_to = $event"
            />
          </div>
          <div class="flex items-center justify-between gap-3">
            <span class="text-p-sm text-ink-gray-6">{{
              __('Attach CRM webhook')
            }}</span>
            <Switch v-model="buyForm.use_crm_webhook" size="sm" />
          </div>
          <ErrorMessage v-if="buyError" :message="buyError" />
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          class="w-full"
          :label="__('Buy')"
          :loading="buySaving"
          @click="saveBuy"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import { showSettings } from '@/composables/settings'
import {
  Button,
  Dialog,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  Switch,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const vapiError = ref('')
const releasing = ref('')
const unassigning = ref('')

const editOpen = ref(false)
const editSaving = ref(false)
const editError = ref('')
const editForm = reactive({
  id: '',
  phone_number: '',
  name: '',
  assistant_id: '',
  squad_id: '',
  workflow_id: '',
  server_url: '',
  fallback_number: '',
  use_crm_webhook: false,
})

const assignOpen = ref(false)
const assignSaving = ref(false)
const assignError = ref('')
const assignForm = reactive({ id: '', phone_number: '', user: '' })

const buyOpen = ref(false)
const buySaving = ref(false)
const buyError = ref('')
const buyForm = reactive({
  name: '',
  area_code: '',
  assistant_id: '',
  assign_to: '',
  use_crm_webhook: true,
})

const twilioLinking = ref(false)
const twilioLinkError = ref('')
const twilioLink = reactive({ phone_number: '', user: '' })

const vapiNumbers = createResource({
  url: 'crm.vapi.api.list_vapi_phone_numbers',
  auto: true,
  onSuccess() {
    vapiError.value = ''
  },
  onError: (err) => {
    vapiError.value =
      err?.messages?.join('\n') ||
      err?.message ||
      __('Could not load Vapi numbers')
  },
})

const assistants = createResource({
  url: 'crm.vapi.api.list_vapi_assistants',
  auto: true,
  onError: () => {},
})

const squads = createResource({
  url: 'crm.vapi.api.list_vapi_squads',
  auto: true,
  onError: () => {},
})

const assignments = createResource({
  url: 'crm.vapi.api.list_assignments',
  auto: true,
  onError: (err) => {
    err?.messages?.forEach((msg) => toast.error(msg))
  },
})

const twilioNumbers = createResource({
  url: 'crm.vapi.api.list_twilio_numbers_for_link',
  auto: true,
  onError: () => {},
})

const assistantOptions = computed(() => [
  { label: __('None / clear'), value: '' },
  ...((assistants.data || []).map((a) => ({
    label: a.name || a.id,
    value: a.id,
  })) || []),
])

const squadOptions = computed(() => [
  { label: __('None / clear'), value: '' },
  ...((squads.data || []).map((s) => ({
    label: s.name || s.id,
    value: s.id,
  })) || []),
])

const twilioNumberOptions = computed(() => {
  const rows = twilioNumbers.data || []
  return [
    { label: __('Select a number'), value: '' },
    ...rows.map((n) => ({
      label: n.ai_linked
        ? `${n.phone_number} (${__('linked')} → ${n.ai_user_name || n.ai_user})`
        : n.phone_number,
      value: n.phone_number,
    })),
  ]
})

function shortId(id) {
  if (!id) return ''
  return id.length > 10 ? `${id.slice(0, 8)}…` : id
}

function reload() {
  vapiError.value = ''
  vapiNumbers.reload()
  assistants.reload()
  squads.reload()
  assignments.reload()
  twilioNumbers.reload()
}

function openUsage() {
  showSettings.value = false
  router.push({ name: 'AI Caller Usage' })
}

function openEdit(row) {
  editError.value = ''
  editForm.id = row.id
  editForm.phone_number = row.phone_number || ''
  editForm.name = row.name || ''
  editForm.assistant_id = row.assistant_id || ''
  editForm.squad_id = row.squad_id || ''
  editForm.workflow_id = row.workflow_id || ''
  editForm.server_url = row.server_url || ''
  editForm.fallback_number = row.fallback_number || ''
  editForm.use_crm_webhook = false
  editOpen.value = true
}

async function saveEdit() {
  if (!editForm.id) return
  editSaving.value = true
  editError.value = ''
  try {
    const payload = {
      phone_id: editForm.id,
      name: editForm.name,
      assistant_id: editForm.assistant_id,
      squad_id: editForm.squad_id,
      workflow_id: editForm.workflow_id,
      fallback_number: editForm.fallback_number,
      clear_assistant: editForm.assistant_id ? 0 : 1,
      clear_squad: editForm.squad_id ? 0 : 1,
      clear_workflow: editForm.workflow_id ? 0 : 1,
    }
    if (editForm.use_crm_webhook) {
      payload.use_crm_webhook = 1
    } else {
      payload.server_url = editForm.server_url
    }
    await call('crm.vapi.api.update_vapi_phone_number', payload)
    toast.success(__('Number updated'))
    editOpen.value = false
    reload()
  } catch (err) {
    editError.value =
      err?.messages?.join('\n') || err?.message || __('Could not save')
  } finally {
    editSaving.value = false
  }
}

function openAssign(row) {
  assignError.value = ''
  assignForm.id = row.id
  assignForm.phone_number = row.phone_number || ''
  assignForm.user = row.ai_user || ''
  assignOpen.value = true
}

async function saveAssign() {
  if (!assignForm.id || !assignForm.user) return
  assignSaving.value = true
  assignError.value = ''
  try {
    await call('crm.vapi.api.link_vapi_number', {
      phone_id: assignForm.id,
      user: assignForm.user,
    })
    toast.success(__('Number assigned'))
    assignOpen.value = false
    reload()
  } catch (err) {
    assignError.value =
      err?.messages?.join('\n') || err?.message || __('Could not assign')
  } finally {
    assignSaving.value = false
  }
}

function openBuy() {
  buyError.value = ''
  buyForm.name = ''
  buyForm.area_code = ''
  buyForm.assistant_id = ''
  buyForm.assign_to = ''
  buyForm.use_crm_webhook = true
  buyOpen.value = true
}

async function saveBuy() {
  buySaving.value = true
  buyError.value = ''
  try {
    await call('crm.vapi.api.create_vapi_phone_number', {
      name: buyForm.name || null,
      area_code: buyForm.area_code || null,
      assistant_id: buyForm.assistant_id || null,
      assign_to: buyForm.assign_to || null,
      use_crm_webhook: buyForm.use_crm_webhook ? 1 : 0,
    })
    toast.success(__('Vapi number created'))
    buyOpen.value = false
    reload()
  } catch (err) {
    buyError.value =
      err?.messages?.join('\n') || err?.message || __('Could not buy number')
  } finally {
    buySaving.value = false
  }
}

async function releaseNumber(row) {
  if (
    !confirm(
      __('Release {0}? This deletes it from your Vapi account.').replace(
        '{0}',
        row.phone_number || row.id,
      ),
    )
  ) {
    return
  }
  releasing.value = row.id
  try {
    await call('crm.vapi.api.delete_vapi_phone_number', { phone_id: row.id })
    toast.success(__('Number released'))
    reload()
  } catch (err) {
    toast.error(
      err?.messages?.[0] || err?.message || __('Could not release number'),
    )
  } finally {
    releasing.value = ''
  }
}

async function unassign(user) {
  unassigning.value = user
  try {
    await call('crm.vapi.api.unassign_agent', { user })
    toast.success(__('Unassigned'))
    reload()
  } catch (err) {
    err?.messages?.forEach((msg) => toast.error(msg))
  } finally {
    unassigning.value = ''
  }
}

async function importTwilio() {
  if (!twilioLink.phone_number || !twilioLink.user) return
  twilioLinking.value = true
  twilioLinkError.value = ''
  try {
    await call('crm.vapi.api.link_and_assign', {
      phone_number: twilioLink.phone_number,
      user: twilioLink.user,
    })
    toast.success(__('Number linked and assigned'))
    twilioLink.phone_number = ''
    twilioLink.user = ''
    reload()
  } catch (err) {
    twilioLinkError.value =
      err?.messages?.join('\n') || err?.message || __('Could not link number')
  } finally {
    twilioLinking.value = false
  }
}
</script>
