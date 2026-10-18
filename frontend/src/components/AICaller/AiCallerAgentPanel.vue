<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row">
    <div
      class="flex w-full shrink-0 flex-col border-b border-outline-gray-modals lg:w-56 lg:border-b-0 lg:border-r"
    >
      <div class="border-b border-outline-gray-modals px-4 py-3">
        <div class="text-p-base-medium text-ink-gray-8">
          {{ __('AI Agent') }}
        </div>
        <p class="mt-0.5 text-p-sm text-ink-gray-5">
          {{ __('Your assigned AI caller agent.') }}
        </p>
      </div>
      <div class="flex-1 overflow-y-auto p-2">
        <div
          v-if="!assignment"
          class="px-2 py-8 text-center text-p-sm text-ink-gray-5"
        >
          {{ __('No agent assigned yet.') }}
        </div>
        <button
          v-else
          type="button"
          class="w-full rounded-5 bg-surface-gray-2 px-3 py-2.5 text-left"
        >
          <div class="truncate text-p-sm-medium text-ink-gray-8">
            {{ assignment.user_name || __('My agent') }}
          </div>
          <div class="mt-0.5 truncate text-p-sm text-ink-gray-5">
            {{ assignment.phone_number || __('No number') }}
          </div>
        </button>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
      <template v-if="!assignment">
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Ask a manager to assign a phone number under Settings → AI Caller.',
            )
          }}
        </p>
        <Button
          v-if="isManager"
          class="mt-4"
          variant="solid"
          :label="__('Open AI Caller settings')"
          @click="$emit('open-settings')"
        />
      </template>
      <template v-else>
        <h2 class="text-xl-semibold text-ink-gray-9">
          {{ assignment.user_name || __('My agent') }}
        </h2>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{
            __(
              'Voice, script, and compliance for your outbound AI calls.',
            )
          }}
        </p>

        <div class="mt-6 max-w-lg space-y-4">
          <FormControl
            :model-value="assignment.phone_number || ''"
            type="text"
            :label="__('Phone number')"
            disabled
          />
          <FormControl
            v-model="form.voice_id"
            type="select"
            :label="__('Voice')"
            :options="voiceOptions"
          />
          <FormControl
            v-model="form.script_id"
            type="select"
            :label="__('Script')"
            :options="scriptOptions"
          />
          <div class="flex items-center justify-between gap-3 py-1">
            <div>
              <div class="text-p-sm-medium text-ink-gray-8">
                {{ __('Respect DNC') }}
              </div>
              <p class="text-p-sm text-ink-gray-5">
                {{ __('Skip numbers on your Do Not Call list.') }}
              </p>
            </div>
            <Switch v-model="form.respect_dnc" />
          </div>
          <div class="flex items-center justify-between gap-3 py-1">
            <div>
              <div class="text-p-sm-medium text-ink-gray-8">
                {{ __('Compliance reviewed') }}
              </div>
              <p class="text-p-sm text-ink-gray-5">
                {{ __('Confirm TCPA calling windows before dialing.') }}
              </p>
            </div>
            <Switch v-model="form.reviewed_compliance" />
          </div>
          <ErrorMessage v-if="error" :message="error" />
          <Button
            variant="solid"
            :label="__('Save agent')"
            :loading="saving"
            @click="save"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import {
  AI_CALLER_SCRIPTS,
  AI_CALLER_VOICES,
} from '@/composables/aiCallerSetup'
import { Button, ErrorMessage, FormControl, Switch, call, toast } from 'frappe-ui'
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  assignment: { type: Object, default: null },
  isManager: { type: Boolean, default: false },
})

const emit = defineEmits(['open-settings', 'saved'])

const saving = ref(false)
const error = ref('')
const form = reactive({
  voice_id: 'warm',
  script_id: 'term',
  respect_dnc: true,
  reviewed_compliance: false,
})

const voiceOptions = AI_CALLER_VOICES.map((v) => ({
  label: v.label,
  value: v.id,
}))

const scriptOptions = AI_CALLER_SCRIPTS.map((s) => ({
  label: s.label,
  value: s.id,
}))

watch(
  () => props.assignment,
  (a) => {
    if (!a) return
    form.voice_id = a.voice_id || 'warm'
    form.script_id = a.script_id || (a.custom_script ? 'custom' : 'term')
    form.respect_dnc = a.respect_dnc !== false && a.respect_dnc !== 0
    form.reviewed_compliance = Boolean(a.reviewed_compliance)
  },
  { immediate: true },
)

async function save() {
  if (!props.assignment) return
  saving.value = true
  error.value = ''
  try {
    const data = await call('crm.vapi.api.sync_my_setup', {
      voice_id: form.voice_id,
      script_id: form.script_id,
      custom_script: form.script_id === 'custom' ? 1 : 0,
      respect_dnc: form.respect_dnc ? 1 : 0,
      reviewed_compliance: form.reviewed_compliance ? 1 : 0,
      setup_completed: 1,
    })
    toast.success(__('Agent saved'))
    emit('saved', data)
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || __('Could not save agent')
  } finally {
    saving.value = false
  }
}
</script>
