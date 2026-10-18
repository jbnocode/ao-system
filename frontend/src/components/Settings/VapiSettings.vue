<template>
  <div class="flex h-full flex-col overflow-y-auto p-8 text-ink-gray-8">
    <div class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h2 class="mb-1 text-2xl-semibold">{{ __('Vapi') }}</h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Connect AI Caller for outbound calling. Buy numbers under Telephony, then link them under AI Caller.',
            )
          }}
        </p>
      </div>
      <Button
        v-if="form.dashboard_url"
        variant="subtle"
        icon-left="lucide-external-link"
        :label="__('Open Vapi dashboard')"
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
          v-model="form.dashboard_url"
          :label="__('Dashboard URL')"
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
  dashboard_url: 'https://dashboard.vapi.ai',
  webhook_secret: '',
})

const voiceOptions = computed(() => [
  { label: __('Warm & professional'), value: 'warm' },
  { label: __('Upbeat & engaging'), value: 'energetic' },
  { label: __('Steady & consultative'), value: 'steady' },
])

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await call('crm.vapi.api.get_vapi_settings')
    form.enabled = !!data.enabled
    form.public_key = data.public_key || ''
    form.default_voice_id = data.default_voice_id || 'warm'
    form.dashboard_url = data.dashboard_url || 'https://dashboard.vapi.ai'
    form.private_api_key = ''
    form.webhook_secret = ''
    hasPrivateKey.value = !!data.has_private_key
    hasWebhookSecret.value = !!data.has_webhook_secret
    webhookUrl.value = data.webhook_url || ''
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || __('Could not load Vapi settings'))
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
  window.open(form.dashboard_url || 'https://dashboard.vapi.ai', '_blank')
}
</script>
