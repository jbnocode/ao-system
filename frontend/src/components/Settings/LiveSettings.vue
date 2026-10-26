<template>
  <div class="flex h-full min-h-0 flex-col">
    <SettingsLayoutBase
      :title="__('AI Live')"
      :description="
        __(
          'OpenAI GPT-Live keys, default voice, calling hours, and Twilio media bridge / SIP for phone AI.',
        )
      "
    >
      <template #header-actions>
        <Button
          variant="subtle"
          icon-left="lucide-refresh-cw"
          :label="__('Refresh')"
          :loading="loading"
          @click="reload"
        />
      </template>

      <template #content>
        <div v-if="loading && !loaded" class="flex justify-center py-12">
          <LoadingIndicator class="w-4" />
        </div>
        <template v-else>
          <div class="mb-2 text-base-semibold text-ink-gray-9">
            {{ __('Connection') }}
          </div>
          <div class="mb-8 max-w-xl space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-base text-ink-gray-7">{{ __('Enabled') }}</span>
              <Switch v-model="form.enabled" size="sm" />
            </div>
            <FormControl
              v-model="form.openai_api_key"
              :label="__('OpenAI API Key')"
              type="password"
              :placeholder="
                hasKey ? __('•••••••• (saved — leave blank to keep)') : 'sk-proj-…'
              "
            />
            <p class="text-p-sm text-ink-gray-5 -mt-2">
              {{
                __(
                  'Project key with GPT-Live access. Stored server-side only — never sent to the browser.',
                )
              }}
            </p>
            <FormControl
              v-model="form.openai_project_id"
              :label="__('OpenAI Project ID (optional)')"
              type="text"
              placeholder="proj_…"
            />
            <FormControl
              v-model="form.webhook_secret"
              :label="__('Webhook secret')"
              type="password"
              :placeholder="
                hasWebhookSecret
                  ? __('•••••••• (saved — leave blank to keep)')
                  : ''
              "
            />
            <p class="text-p-sm text-ink-gray-5 -mt-2">
              {{
                __(
                  'Shared with the media bridge (X-CRM-Live-Secret / Bearer). Required for phone AI.',
                )
              }}
            </p>
          </div>

          <div class="mb-2 text-base-semibold text-ink-gray-9">
            {{ __('Defaults') }}
          </div>
          <div class="mb-8 max-w-xl space-y-4">
            <FormControl
              v-model="form.default_voice_id"
              :label="__('Default built-in voice')"
              type="select"
              :options="voiceOptions"
            />
            <FormControl
              v-model="form.default_script_id"
              :label="__('Default script')"
              type="select"
              :options="scriptOptions"
            />
            <FormControl
              v-model="form.default_live_voice_id"
              :label="__('Default prompt voice ID')"
              type="text"
              placeholder="voice_…"
            />
            <FormControl
              v-model="form.default_live_voice_prompt"
              :label="__('Default voice prompt')"
              type="textarea"
            />
            <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div class="min-w-0 flex-1">
                <FormControl
                  v-model="form.calling_hours_start"
                  type="select"
                  :label="__('Calling hours start')"
                  :options="hourStartOptions"
                />
              </div>
              <div class="min-w-0 flex-1">
                <FormControl
                  v-model="form.calling_hours_end"
                  type="select"
                  :label="__('Calling hours end')"
                  :options="hourEndOptions"
                />
              </div>
            </div>
            <p class="text-p-sm text-ink-gray-5 -mt-2">
              {{
                __('Site timezone: {0}.', [timezone || '—'])
              }}
            </p>
          </div>

          <div class="mb-2 text-base-semibold text-ink-gray-9">
            {{ __('Twilio bridge') }}
          </div>
          <p class="mb-4 text-p-sm text-ink-gray-6">
            {{
              __(
                'Set Media Stream URL to the AO Live media bridge (wss://…/media), or configure OpenAI SIP for outbound.',
              )
            }}
          </p>
          <div class="mb-8 max-w-xl space-y-4">
            <FormControl
              v-model="form.media_stream_url"
              :label="__('Media Stream URL')"
              type="text"
              placeholder="wss://bridge.example.com/media"
            />
            <FormControl
              v-model="form.sip_provider_url"
              :label="__('SIP provider URL')"
              type="text"
              placeholder="sips:…"
            />
            <FormControl
              v-model="form.sip_username"
              :label="__('SIP username')"
              type="text"
            />
            <FormControl
              v-model="form.sip_password"
              :label="__('SIP password')"
              type="password"
              :placeholder="
                hasSipPassword
                  ? __('•••••••• (saved — leave blank to keep)')
                  : ''
              "
            />
            <p class="text-p-sm text-ink-gray-5">
              {{ __('Inbound voice webhook') }}:
              <span class="break-all text-ink-gray-7">{{
                inboundVoiceUrl || '—'
              }}</span>
            </p>
          </div>

          <ErrorMessage v-if="error" class="mb-4" :message="error" />
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="saving"
            @click="save"
          />

          <div class="mt-10 mb-2 text-base-semibold text-ink-gray-5">
            {{ __('Legacy') }}
          </div>
          <p class="text-p-sm text-ink-gray-5">
            {{
              __(
                'Vapi settings remain under Settings → AI Calling (Legacy) for existing installs. New AI Caller work uses GPT-Live + Twilio only.',
              )
            }}
          </p>
        </template>
      </template>
    </SettingsLayoutBase>
  </div>
</template>

<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import {
  AI_CALLER_SCRIPTS,
  AI_CALLER_VOICES,
} from '@/composables/aiCallerSetup'
import {
  Button,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  Switch,
  call,
  toast,
} from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'

const loading = ref(false)
const loaded = ref(false)
const saving = ref(false)
const error = ref('')
const hasKey = ref(false)
const hasWebhookSecret = ref(false)
const hasSipPassword = ref(false)
const timezone = ref('')
const inboundVoiceUrl = ref('')

const form = reactive({
  enabled: false,
  openai_api_key: '',
  openai_project_id: '',
  webhook_secret: '',
  default_voice_id: 'cedar',
  default_script_id: 'term',
  default_live_voice_id: '',
  default_live_voice_prompt: '',
  calling_hours_start: '8',
  calling_hours_end: '21',
  media_stream_url: '',
  sip_provider_url: '',
  sip_username: '',
  sip_password: '',
})

const voiceOptions = computed(() =>
  AI_CALLER_VOICES.map((v) => ({ label: v.label, value: v.id })),
)

const scriptOptions = computed(() =>
  AI_CALLER_SCRIPTS.map((s) => ({ label: s.label, value: s.id })),
)

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

function formatHour(h, isMidnightNext = false) {
  if (isMidnightNext) return __('12:00 AM (next day)')
  const period = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 || 12
  return `${hour12}:00 ${period}`
}

onMounted(reload)

async function reload() {
  loading.value = true
  error.value = ''
  try {
    const data = await call('crm.live.api.get_live_settings')
    form.enabled = Boolean(data.enabled)
    form.openai_project_id = data.openai_project_id || ''
    form.default_voice_id = data.default_voice_id || 'cedar'
    form.default_script_id = data.default_script_id || 'term'
    form.default_live_voice_id = data.default_live_voice_id || ''
    form.default_live_voice_prompt = data.default_live_voice_prompt || ''
    form.calling_hours_start = String(data.calling_hours_start ?? 8)
    form.calling_hours_end = String(data.calling_hours_end ?? 21)
    form.media_stream_url = data.media_stream_url || ''
    form.sip_provider_url = data.sip_provider_url || ''
    form.sip_username = data.sip_username || ''
    form.openai_api_key = ''
    form.webhook_secret = ''
    form.sip_password = ''
    hasKey.value = Boolean(data.has_openai_key)
    hasWebhookSecret.value = Boolean(data.has_webhook_secret)
    hasSipPassword.value = Boolean(data.has_sip_password)
    timezone.value = data.timezone || ''
    inboundVoiceUrl.value = data.inbound_voice_url || ''
    loaded.value = true
  } catch (e) {
    error.value =
      e?.messages?.join('\n') || e?.message || __('Could not load AI Live settings')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const payload = {
      enabled: form.enabled ? 1 : 0,
      openai_project_id: form.openai_project_id,
      default_voice_id: form.default_voice_id,
      default_script_id: form.default_script_id,
      default_live_voice_id: form.default_live_voice_id,
      default_live_voice_prompt: form.default_live_voice_prompt,
      calling_hours_start: form.calling_hours_start,
      calling_hours_end: form.calling_hours_end,
      media_stream_url: form.media_stream_url,
      sip_provider_url: form.sip_provider_url,
      sip_username: form.sip_username,
    }
    if (form.openai_api_key) payload.openai_api_key = form.openai_api_key
    if (form.webhook_secret) payload.webhook_secret = form.webhook_secret
    if (form.sip_password) payload.sip_password = form.sip_password
    await call('crm.live.api.save_live_settings', payload)
    toast.success(__('AI Live settings saved'))
    await reload()
  } catch (e) {
    error.value =
      e?.messages?.join('\n') || e?.message || __('Could not save settings')
  } finally {
    saving.value = false
  }
}
</script>
