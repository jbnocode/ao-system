<template>
  <div class="flex h-full min-h-0 flex-col">
    <SettingsLayoutBase
      :title="__('AI Caller')"
      :description="
        __(
          'Org defaults, Twilio numbers, and agent voice / script assignment for GPT-Live outbound and inbound.',
        )
      "
    >
      <template #header-actions>
        <div class="flex shrink-0 flex-wrap items-center justify-end gap-2">
          <Button
            variant="subtle"
            :label="__('Usage dashboard')"
            @click="openUsage"
          />
          <Button
            variant="subtle"
            :label="__('Get a number')"
            @click="openBuy"
          />
          <Button
            variant="subtle"
            icon-left="lucide-refresh-cw"
            :label="__('Refresh')"
            :loading="
              phoneNumbers.loading || assignments.loading || defaults.loading
            "
            @click="reload"
          />
        </div>
      </template>

      <template #content>
        <!-- Defaults -->
        <div class="mb-2 text-base-semibold text-ink-gray-9">
          {{ __('Defaults') }}
        </div>
        <p class="mb-4 text-p-sm text-ink-gray-6">
          {{
            __(
              'Applied when a new agent is assigned. Existing agents keep their own voice and script until you edit them.',
            )
          }}
        </p>
        <div
          v-if="defaults.loading && !defaults.data"
          class="mb-8 flex justify-center py-6"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div v-else class="mb-8 max-w-2xl space-y-4">
          <FormControl
            v-model="defaultsForm.default_voice_id"
            type="select"
            :label="__('Default voice')"
            :options="voiceOptions"
          />
          <FormControl
            v-model="defaultsForm.default_script_id"
            type="select"
            :label="__('Default script')"
            :options="scriptOptions"
          />
          <FormControl
            v-model="defaultsForm.default_live_voice_prompt"
            type="textarea"
            :label="__('Default voice prompt (optional)')"
          />
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div class="min-w-0 flex-1">
              <FormControl
                v-model="defaultsForm.calling_hours_start"
                type="select"
                :label="__('Calling hours start')"
                :options="hourStartOptions"
              />
            </div>
            <div class="min-w-0 flex-1">
              <FormControl
                v-model="defaultsForm.calling_hours_end"
                type="select"
                :label="__('Calling hours end')"
                :options="hourEndOptions"
              />
            </div>
          </div>
          <p class="text-p-sm text-ink-gray-5 -mt-2">
            {{
              __(
                'Site timezone: {0}. Outbound AI calls outside this window are blocked.',
                [defaults.data?.timezone || '—'],
              )
            }}
          </p>
          <div
            v-if="!defaults.data?.enabled || !defaults.data?.has_openai_key"
            class="text-p-sm text-ink-gray-5"
          >
            {{
              __(
                'AI Live is not fully connected yet. A System Manager must enable it and save an OpenAI key under Settings → AI Live.',
              )
            }}
          </div>
          <ErrorMessage v-if="defaultsError" :message="defaultsError" />
          <Button
            variant="solid"
            :label="__('Save defaults')"
            :loading="defaultsSaving"
            @click="saveDefaults"
          />
        </div>

        <!-- Phone numbers (Twilio) -->
        <div class="mb-2 text-base-semibold text-ink-gray-9">
          {{ __('Twilio phone numbers') }}
        </div>
        <p class="mb-4 text-p-sm text-ink-gray-6">
          {{
            __(
              'Buy or reuse Twilio numbers, then assign them to agents. SMS stays on the same line.',
            )
          }}
        </p>

        <div
          v-if="phoneNumbers.loading && !phoneNumbers.data?.length"
          class="flex justify-center py-10"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div v-else-if="phoneError" class="mb-6">
          <ErrorMessage :message="phoneError" />
          <p class="mt-2 text-p-sm text-ink-gray-5">
            {{
              __(
                'Connect Twilio under Settings → Telephony, then refresh.',
              )
            }}
          </p>
        </div>
        <div
          v-else-if="!phoneNumbers.data?.length"
          class="mb-8 border-b border-outline-gray-modals py-8 text-center text-p-sm text-ink-gray-5"
        >
          {{
            __('No Twilio numbers yet. Get a number above, or buy one under Telephony.')
          }}
        </div>
        <div v-else class="mb-8 flex flex-col">
          <div
            v-for="row in phoneNumbers.data"
            :key="row.sid || row.phone_number"
            class="border-b border-outline-gray-modals py-3"
          >
            <div
              class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
            >
              <div class="min-w-0">
                <div class="text-p-base-medium text-ink-gray-8">
                  {{ row.phone_number }}
                  <span
                    v-if="row.friendly_name"
                    class="text-p-sm font-normal text-ink-gray-5"
                  >
                    · {{ row.friendly_name }}
                  </span>
                </div>
                <div class="text-p-sm text-ink-gray-5">
                  <span v-if="row.ai_linked">
                    {{ __('AI assigned to') }}
                    {{ row.ai_user_name || row.ai_user }}
                  </span>
                  <span v-else-if="row.assigned_to">
                    {{ __('Telephony') }}
                    {{
                      row.assigned_to.full_name ||
                      row.assigned_to.user ||
                      row.assigned_to
                    }}
                  </span>
                  <span v-else>{{ __('Unassigned') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Agents + assign -->
        <div class="mb-2 text-base-semibold text-ink-gray-9">
          {{ __('Agents') }}
        </div>
        <p class="mb-4 text-p-sm text-ink-gray-6">
          {{
            __(
              'Assign a Twilio number to a CRM user, then set voice, script, and compliance.',
            )
          }}
        </p>

        <div class="mb-6 max-w-2xl space-y-4">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div class="min-w-0 flex-1">
              <FormControl
                v-model="assignForm.user"
                type="select"
                :label="__('User')"
                :options="userOptions"
              />
            </div>
            <div class="min-w-0 flex-1">
              <FormControl
                v-model="assignForm.phone_number"
                type="select"
                :label="__('Phone number')"
                :options="assignPhoneOptions"
              />
            </div>
            <Button
              variant="solid"
              :label="__('Assign')"
              :loading="assignSaving"
              :disabled="!assignForm.user || !assignForm.phone_number"
              @click="saveAssign"
            />
          </div>
          <ErrorMessage v-if="assignError" :message="assignError" />
        </div>

        <div
          v-if="assignments.loading && !assignments.data?.length"
          class="flex justify-center py-10"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div
          v-else-if="!assignments.data?.length"
          class="mb-8 border-b border-outline-gray-modals py-8 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No agents yet. Pick a user and phone number above.') }}
        </div>
        <div v-else class="mb-8 flex flex-col">
          <div
            v-for="row in assignments.data"
            :key="row.name"
            class="border-b border-outline-gray-modals py-3"
          >
            <div
              class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
            >
              <div class="min-w-0">
                <div class="text-p-base-medium text-ink-gray-8">
                  {{ row.user_name || row.user }}
                </div>
                <div class="text-p-sm text-ink-gray-5">
                  {{ row.phone_number || __('No number') }}
                  <span v-if="voiceLabel(row.voice_id)">
                    · {{ voiceLabel(row.voice_id) }}
                  </span>
                  <span v-if="scriptLabel(row)">
                    · {{ scriptLabel(row) }}
                  </span>
                  <span v-if="row.respect_dnc"> · {{ __('DNC on') }}</span>
                  <span v-else> · {{ __('DNC off') }}</span>
                  <span v-if="row.setup_completed"> · {{ __('Ready') }}</span>
                  <span v-else> · {{ __('Setup pending') }}</span>
                </div>
              </div>
              <div class="flex shrink-0 flex-wrap gap-2">
                <Button
                  size="sm"
                  :variant="agentForm.user === row.user ? 'solid' : 'subtle'"
                  :label="
                    agentForm.user === row.user ? __('Close') : __('Configure')
                  "
                  @click="toggleAgentEdit(row)"
                />
                <Button
                  size="sm"
                  variant="subtle"
                  :label="__('Unassign')"
                  :loading="unassigning === row.user"
                  @click="unassign(row.user)"
                />
              </div>
            </div>

            <div
              v-if="agentForm.user === row.user"
              class="mt-4 max-w-2xl space-y-4 pb-2"
            >
              <FormControl
                v-model="agentForm.voice_id"
                type="select"
                :label="__('Built-in voice')"
                :options="voiceOptions"
              />
              <FormControl
                v-model="agentForm.script_id"
                type="select"
                :label="__('Script / talk track')"
                :options="scriptOptions"
              />
              <FormControl
                v-model="agentForm.live_voice_id"
                type="text"
                :label="__('Prompt voice ID (optional)')"
                placeholder="voice_…"
              />
              <FormControl
                v-model="agentForm.live_voice_prompt"
                type="textarea"
                :label="__('Voice prompt (optional)')"
              />
              <div class="flex items-center justify-between gap-3 py-1">
                <div>
                  <div class="text-p-sm-medium text-ink-gray-8">
                    {{ __('Respect DNC') }}
                  </div>
                  <p class="text-p-sm text-ink-gray-5">
                    {{ __('Skip numbers marked Do Not Call / Do Not Contact.') }}
                  </p>
                </div>
                <Switch v-model="agentForm.respect_dnc" size="sm" />
              </div>
              <div class="flex items-center justify-between gap-3 py-1">
                <div>
                  <div class="text-p-sm-medium text-ink-gray-8">
                    {{ __('Compliance reviewed') }}
                  </div>
                  <p class="text-p-sm text-ink-gray-5">
                    {{ __('Agent acknowledged AI disclosure and calling rules.') }}
                  </p>
                </div>
                <Switch v-model="agentForm.reviewed_compliance" size="sm" />
              </div>
              <div class="flex items-center justify-between gap-3 py-1">
                <div>
                  <div class="text-p-sm-medium text-ink-gray-8">
                    {{ __('Setup completed') }}
                  </div>
                </div>
                <Switch v-model="agentForm.setup_completed" size="sm" />
              </div>
              <ErrorMessage v-if="agentError" :message="agentError" />
              <div class="flex flex-wrap gap-2">
                <Button
                  variant="solid"
                  :label="__('Save agent')"
                  :loading="agentSaving"
                  @click="saveAgent"
                />
                <Button
                  variant="subtle"
                  :label="__('Cancel')"
                  :disabled="agentSaving"
                  @click="closeAgentEdit"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </SettingsLayoutBase>

    <Dialog v-model="buyOpen" :options="{ title: __('Get a phone number') }">
      <template #body-content>
        <div class="space-y-4">
          <FormControl
            v-model="buyForm.phone_number"
            type="text"
            :label="__('E.164 number to buy')"
            placeholder="+1725…"
          />
          <p class="text-p-sm text-ink-gray-5 -mt-2">
            {{
              __(
                'Search available numbers under Settings → Telephony, then paste the E.164 here to purchase.',
              )
            }}
          </p>
          <FormControl
            v-model="buyForm.friendly_name"
            type="text"
            :label="__('Display name (optional)')"
          />
          <FormControl
            v-model="buyForm.assign_to"
            type="select"
            :label="__('Assign to (optional)')"
            :options="userOptions"
          />
          <ErrorMessage v-if="buyError" :message="buyError" />
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          class="w-full"
          :label="__('Get number')"
          :loading="buySaving"
          :disabled="!buyForm.phone_number"
          @click="saveBuy"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import {
  AI_CALLER_SCRIPTS,
  AI_CALLER_VOICES,
} from '@/composables/aiCallerSetup'
import { showSettings } from '@/composables/settings'
import { usersStore } from '@/stores/users'
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
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const { users } = usersStore()
const router = useRouter()

const phoneError = ref('')
const unassigning = ref('')

const defaultsSaving = ref(false)
const defaultsError = ref('')
const defaultsForm = reactive({
  default_voice_id: 'cedar',
  default_script_id: 'term',
  default_live_voice_prompt: '',
  calling_hours_start: '8',
  calling_hours_end: '21',
})

const assignSaving = ref(false)
const assignError = ref('')
const assignForm = reactive({ phone_number: '', user: '' })

const agentSaving = ref(false)
const agentError = ref('')
const agentForm = reactive({
  user: '',
  user_name: '',
  phone_number: '',
  voice_id: 'cedar',
  script_id: 'term',
  live_voice_id: '',
  live_voice_prompt: '',
  respect_dnc: true,
  reviewed_compliance: false,
  setup_completed: false,
})

const buyOpen = ref(false)
const buySaving = ref(false)
const buyError = ref('')
const buyForm = reactive({
  phone_number: '',
  friendly_name: '',
  assign_to: '',
})

const defaults = createResource({
  url: 'crm.live.api.get_live_settings',
  auto: true,
  onError: () => {},
})

watch(
  () => defaults.data,
  (data) => {
    if (!data) return
    defaultsForm.default_voice_id = data.default_voice_id || 'cedar'
    defaultsForm.default_script_id = data.default_script_id || 'term'
    defaultsForm.default_live_voice_prompt =
      data.default_live_voice_prompt || ''
    defaultsForm.calling_hours_start = String(data.calling_hours_start ?? 8)
    defaultsForm.calling_hours_end = String(data.calling_hours_end ?? 21)
  },
  { immediate: true },
)

const phoneNumbers = createResource({
  url: 'crm.live.api.list_twilio_numbers_for_assign',
  auto: true,
  onSuccess() {
    phoneError.value = ''
  },
  onError: (err) => {
    phoneError.value =
      err?.messages?.join('\n') ||
      err?.message ||
      __('Could not load phone numbers')
  },
})

const assignments = createResource({
  url: 'crm.live.api.list_assignments',
  auto: true,
  onError: (err) => {
    err?.messages?.forEach((msg) => toast.error(msg))
  },
})

const voiceOptions = computed(() => {
  const fromCatalog = defaults.data?.catalog?.voices
  if (fromCatalog?.length) {
    return fromCatalog.map((v) => ({ label: v.label, value: v.id }))
  }
  return AI_CALLER_VOICES.map((v) => ({ label: v.label, value: v.id }))
})

const scriptOptions = computed(() => {
  const fromCatalog = defaults.data?.catalog?.scripts
  if (fromCatalog?.length) {
    return fromCatalog.map((s) => ({ label: s.label, value: s.id }))
  }
  return AI_CALLER_SCRIPTS.map((s) => ({ label: s.label, value: s.id }))
})

const hourStartOptions = computed(() =>
  Array.from({ length: 24 }, (_, h) => ({
    label: formatHour(h),
    value: String(h),
  })),
)

const hourEndOptions = computed(() =>
  Array.from({ length: 24 }, (_, i) => {
    const h = i + 1
    return { label: formatHour(h === 24 ? 0 : h, h === 24), value: String(h) }
  }),
)

const userOptions = computed(() => [
  { label: __('Select a user'), value: '' },
  ...((users.data?.crmUsers || [])
    .filter((u) => u.name && u.name !== 'Administrator')
    .map((u) => ({
      label: u.full_name ? `${u.full_name} (${u.name})` : u.name,
      value: u.name,
    })) || []),
])

const assignPhoneOptions = computed(() => [
  { label: __('Select a number'), value: '' },
  ...((phoneNumbers.data || []).map((n) => ({
    label: n.ai_linked
      ? `${n.phone_number} → ${n.ai_user_name || n.ai_user}`
      : n.phone_number,
    value: n.phone_number,
  })) || []),
])

function formatHour(h, isMidnightNext = false) {
  if (isMidnightNext) return __('12:00 AM (next day)')
  const period = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 || 12
  return `${hour12}:00 ${period}`
}

function voiceLabel(id) {
  if (!id) return ''
  return voiceOptions.value.find((v) => v.value === id)?.label || id
}

function scriptLabel(row) {
  const id = row?.script_id || (row?.custom_script ? 'custom' : '')
  if (!id) return ''
  return scriptOptions.value.find((s) => s.value === id)?.label || id
}

function reload() {
  phoneError.value = ''
  defaults.reload()
  phoneNumbers.reload()
  assignments.reload()
}

function openUsage() {
  showSettings.value = false
  router.push({ name: 'AI Caller Usage' })
}

async function saveDefaults() {
  defaultsSaving.value = true
  defaultsError.value = ''
  try {
    await call('crm.live.api.save_ai_caller_defaults', {
      default_voice_id: defaultsForm.default_voice_id,
      default_script_id: defaultsForm.default_script_id,
      default_live_voice_prompt: defaultsForm.default_live_voice_prompt,
      calling_hours_start: defaultsForm.calling_hours_start,
      calling_hours_end: defaultsForm.calling_hours_end,
    })
    toast.success(__('Defaults saved'))
    defaults.reload()
  } catch (err) {
    defaultsError.value =
      err?.messages?.join('\n') || err?.message || __('Could not save defaults')
  } finally {
    defaultsSaving.value = false
  }
}

async function saveAssign() {
  if (!assignForm.phone_number || !assignForm.user) return
  assignSaving.value = true
  assignError.value = ''
  try {
    await call('crm.live.api.assign_twilio_number', {
      phone_number: assignForm.phone_number,
      user: assignForm.user,
    })
    toast.success(__('Number assigned'))
    assignForm.phone_number = ''
    assignForm.user = ''
    reload()
  } catch (err) {
    assignError.value =
      err?.messages?.join('\n') || err?.message || __('Could not assign')
  } finally {
    assignSaving.value = false
  }
}

function closeAgentEdit() {
  agentError.value = ''
  agentForm.user = ''
  agentForm.user_name = ''
  agentForm.phone_number = ''
  agentForm.voice_id = 'cedar'
  agentForm.script_id = 'term'
  agentForm.live_voice_id = ''
  agentForm.live_voice_prompt = ''
  agentForm.respect_dnc = true
  agentForm.reviewed_compliance = false
  agentForm.setup_completed = false
}

function toggleAgentEdit(row) {
  if (agentForm.user === row.user) {
    closeAgentEdit()
    return
  }
  agentError.value = ''
  agentForm.user = row.user
  agentForm.user_name = row.user_name || ''
  agentForm.phone_number = row.phone_number || ''
  agentForm.voice_id = row.voice_id || 'cedar'
  agentForm.script_id =
    row.script_id || (row.custom_script ? 'custom' : 'term')
  agentForm.live_voice_id = row.live_voice_id || ''
  agentForm.live_voice_prompt = row.live_voice_prompt || ''
  agentForm.respect_dnc = row.respect_dnc !== false && row.respect_dnc !== 0
  agentForm.reviewed_compliance = Boolean(row.reviewed_compliance)
  agentForm.setup_completed = Boolean(row.setup_completed)
}

async function saveAgent() {
  if (!agentForm.user) return
  agentSaving.value = true
  agentError.value = ''
  try {
    await call('crm.live.api.update_agent_assignment', {
      user: agentForm.user,
      voice_id: agentForm.voice_id,
      script_id: agentForm.script_id,
      custom_script: agentForm.script_id === 'custom' ? 1 : 0,
      respect_dnc: agentForm.respect_dnc ? 1 : 0,
      reviewed_compliance: agentForm.reviewed_compliance ? 1 : 0,
      setup_completed: agentForm.setup_completed ? 1 : 0,
      live_voice_id: agentForm.live_voice_id,
      live_voice_prompt: agentForm.live_voice_prompt,
    })
    toast.success(__('Agent saved'))
    closeAgentEdit()
    assignments.reload()
  } catch (err) {
    agentError.value =
      err?.messages?.join('\n') || err?.message || __('Could not save agent')
  } finally {
    agentSaving.value = false
  }
}

function openBuy() {
  buyError.value = ''
  buyForm.phone_number = ''
  buyForm.friendly_name = ''
  buyForm.assign_to = ''
  buyOpen.value = true
}

async function saveBuy() {
  buySaving.value = true
  buyError.value = ''
  try {
    await call('crm.integrations.twilio.api.purchase_phone_number', {
      phone_number: buyForm.phone_number,
      friendly_name: buyForm.friendly_name || null,
      assign_to: buyForm.assign_to || null,
    })
    if (buyForm.assign_to) {
      await call('crm.live.api.assign_twilio_number', {
        phone_number: buyForm.phone_number,
        user: buyForm.assign_to,
      })
    }
    toast.success(__('Number purchased'))
    buyOpen.value = false
    reload()
  } catch (err) {
    buyError.value =
      err?.messages?.join('\n') || err?.message || __('Could not get number')
  } finally {
    buySaving.value = false
  }
}

async function unassign(user) {
  unassigning.value = user
  try {
    await call('crm.live.api.unassign_agent', { user })
    toast.success(__('Unassigned'))
    reload()
  } catch (err) {
    err?.messages?.forEach((msg) => toast.error(msg))
  } finally {
    unassigning.value = ''
  }
}
</script>
