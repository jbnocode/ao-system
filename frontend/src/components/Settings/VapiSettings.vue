<template>
  <div class="flex h-full flex-col overflow-y-auto p-8 text-ink-gray-8">
    <div class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h2 class="mb-1 text-2xl-semibold">{{ __('AI Calling (Legacy)') }}</h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Legacy Vapi keys. New AI Caller work uses Settings → AI Live (GPT-Live) and Twilio. Leave this frozen unless you still run Vapi numbers.',
            )
          }}
        </p>
      </div>
      <Button
        v-if="form.dashboard_url"
        variant="subtle"
        icon-left="lucide-external-link"
        :label="__('Open provider dashboard')"
        @click="openDashboard"
      />
    </div>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingIndicator class="w-4" />
    </div>
    <template v-else>
      <div class="mb-8 max-w-xl space-y-4">
        <div class="flex items-center justify-between">
          <span class="text-base text-ink-gray-7">{{ __('Enabled') }}</span>
          <Switch v-model="form.enabled" size="sm" />
        </div>
        <FormControl
          v-model="form.private_api_key"
          :label="__('Private API Key')"
          type="password"
          :placeholder="
            hasPrivateKey ? __('•••••••• (saved — leave blank to keep)') : ''
          "
        />
        <FormControl
          v-model="form.public_key"
          :label="__('Public Key')"
          type="text"
        />
        <p class="text-p-sm text-ink-gray-5 -mt-2">
          {{ __('Public key is used only for the in-app test widget.') }}
        </p>
        <FormControl
          v-model="form.default_voice_id"
          :label="__('Default voice')"
          type="select"
          :options="voiceOptions"
        />
        <FormControl
          v-model="form.voice_model"
          :label="__('Voice quality')"
          type="select"
          :options="voiceModelOptions"
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
        <FormControl
          v-model="form.dashboard_url"
          :label="__('Provider dashboard URL')"
          type="text"
        />
        <FormControl
          :model-value="webhookUrl"
          :label="__('Webhook URL')"
          type="text"
          readonly
        />
        <p class="text-p-sm text-ink-gray-5 -mt-2">
          {{
            __(
              'Assistants sync this URL automatically. Optional secret below validates inbound webhooks.',
            )
          }}
        </p>
        <FormControl
          v-model="form.webhook_secret"
          :label="__('Webhook Secret')"
          type="password"
          :placeholder="
            hasWebhookSecret
              ? __('•••••••• (saved — leave blank to keep)')
              : ''
          "
        />
        <Button
          variant="solid"
          :label="__('Save')"
          :loading="saving"
          @click="save"
        />
      </div>
    </template>
  </div>
</template>

<script setup>
import {
  Button,
  FormControl,
  LoadingIndicator,
  Switch,
  call,
  toast,
} from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'

const loading = ref(true)
const saving = ref(false)
const hasPrivateKey = ref(false)
const hasWebhookSecret = ref(false)
const webhookUrl = ref('')
const form = reactive({
  enabled: false,
  private_api_key: '',
  public_key: '',
  default_voice_id: 'warm',
  voice_model: 'realistic',
  calling_hours_start: '8',
  calling_hours_end: '21',
  dashboard_url: '',
  webhook_secret: '',
})

const voiceOptions = computed(() => [
  { label: __('Warm & professional'), value: 'warm' },
  { label: __('Upbeat & engaging'), value: 'energetic' },
  { label: __('Steady & consultative'), value: 'steady' },
])

const voiceModelOptions = computed(() => [
  { label: __('Most realistic'), value: 'realistic' },
  { label: __('Balanced'), value: 'balanced' },
  { label: __('Fastest'), value: 'fast' },
])

const hourStartOptions = computed(() =>
  Array.from({ length: 24 }, (_, h) => ({
    label: formatHour(h),
    value: String(h),
  })),
)

const hourEndOptions = computed(() =>
  Array.from({ length: 24 }, (_, i) => {
    const h = i + 1
    return {
      label: formatHour(h === 24 ? 0 : h, h === 24),
      value: String(h),
    }
  }),
)

function formatHour(h, isMidnightNext = false) {
  if (isMidnightNext) return __('12:00 AM (next day)')
  const period = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 || 12
  return `${hour12}:00 ${period}`
}

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await call('crm.vapi.api.get_vapi_settings')
    form.enabled = !!data.enabled
    form.public_key = data.public_key || ''
    form.default_voice_id = data.default_voice_id || 'warm'
    form.voice_model = data.voice_model || 'realistic'
    form.calling_hours_start = String(data.calling_hours_start ?? 8)
    form.calling_hours_end = String(data.calling_hours_end ?? 21)
    form.dashboard_url = data.dashboard_url || ''
    form.private_api_key = ''
    form.webhook_secret = ''
    hasPrivateKey.value = !!data.has_private_key
    hasWebhookSecret.value = !!data.has_webhook_secret
    webhookUrl.value = data.webhook_url || ''
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not load AI calling settings'),
    )
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload = {
      enabled: form.enabled ? 1 : 0,
      public_key: form.public_key,
      default_voice_id: form.default_voice_id,
      voice_model: form.voice_model,
      calling_hours_start: form.calling_hours_start,
      calling_hours_end: form.calling_hours_end,
      dashboard_url: form.dashboard_url,
    }
    if (form.private_api_key) payload.private_api_key = form.private_api_key
    if (form.webhook_secret) payload.webhook_secret = form.webhook_secret
    const data = await call('crm.vapi.api.save_vapi_settings', payload)
    hasPrivateKey.value = !!data.has_private_key
    hasWebhookSecret.value = !!data.has_webhook_secret
    webhookUrl.value = data.webhook_url || webhookUrl.value
    form.private_api_key = ''
    form.webhook_secret = ''
    toast.success(__('Saved'))
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || __('Could not save'))
  } finally {
    saving.value = false
  }
}

function openDashboard() {
  if (form.dashboard_url) window.open(form.dashboard_url, '_blank')
}
</script>
