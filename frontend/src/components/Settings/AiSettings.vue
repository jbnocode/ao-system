<template>
  <div class="flex h-full flex-col overflow-y-auto p-8 text-ink-gray-8">
    <h2 class="mb-1 text-2xl-semibold">{{ __('AI') }}</h2>
    <p class="mb-6 text-p-base text-ink-gray-6">
      {{
        __(
          'Configure the AI provider. Only software admins (System Manager) can change these settings.',
        )
      }}
    </p>

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
          :modelValue="form.provider"
          type="select"
          :label="__('Provider')"
          :options="providerOptions"
          @update:modelValue="onProviderChange"
        />

        <FormControl
          v-if="isBedrock"
          :modelValue="form.aws_region"
          type="select"
          :label="__('AWS Region')"
          :options="regionOptions"
          @update:modelValue="onRegionChange"
        />

        <FormControl
          v-model="form.base_url"
          :label="__('Base URL')"
          type="text"
          :disabled="isBedrock"
        />
        <p v-if="isBedrock" class="-mt-2 text-p-sm text-ink-gray-5">
          {{
            __(
              'Uses Bedrock Runtime OpenAI-compatible Chat Completions for the selected region.',
            )
          }}
        </p>

        <FormControl
          v-if="isBedrock"
          :modelValue="form.model"
          type="select"
          :label="__('Model')"
          :options="bedrockModelOptions"
          @update:modelValue="(v) => (form.model = v)"
        />
        <FormControl
          v-else
          v-model="form.model"
          :label="__('Model')"
          type="text"
        />
        <p v-if="isBedrock" class="-mt-2 text-p-sm text-ink-gray-5">
          {{
            __(
              'Enable model access in the Bedrock console for this region first.',
            )
          }}
        </p>

        <FormControl
          v-model="form.api_key"
          :label="isBedrock ? __('Bedrock API Key') : __('API Key')"
          type="password"
        />
        <p class="-mt-2 text-p-sm text-ink-gray-5">
          {{
            isBedrock
              ? __(
                  'Paste an Amazon Bedrock API key (Bearer). Leave blank to keep the existing key.',
                )
              : __('Leave blank to keep the existing key.')
          }}
        </p>

        <FormControl
          v-model="form.credits_per_request"
          :label="__('Credits per request')"
          type="number"
        />
        <FormControl
          v-model="form.default_grant"
          :label="__('Default grant for new users')"
          type="number"
        />
        <p class="-mt-2 text-p-sm text-ink-gray-5">
          {{
            __(
              'Taken from the team pool when a user first uses AI (0 if the pool is empty). Prefer disbursing from Credits settings.',
            )
          }}
        </p>
        <div class="flex items-center justify-between">
          <span class="text-base text-ink-gray-7">{{
            __('Allow offline demo')
          }}</span>
          <Switch v-model="form.allow_offline_demo" size="sm" />
        </div>

        <div class="flex flex-wrap gap-2 pt-2">
          <Button
            variant="solid"
            :label="__('Save')"
            :loading="saving"
            @click="saveSettings"
          />
          <Button
            variant="subtle"
            :label="__('Test connection')"
            :loading="testing"
            @click="testConnection"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import {
  PROVIDER_BEDROCK,
  PROVIDER_CUSTOM,
  PROVIDER_OPENAI,
  applyProviderPreset,
  bedrockBaseUrl,
} from '@/utils/aiProviders'
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
const testing = ref(false)
const catalog = ref(null)

const form = reactive({
  enabled: true,
  provider: PROVIDER_OPENAI,
  aws_region: 'us-east-1',
  base_url: 'https://api.openai.com/v1',
  model: 'gpt-4o-mini',
  api_key: '',
  credits_per_request: 1,
  default_grant: 0,
  allow_offline_demo: true,
})

const isBedrock = computed(() => form.provider === PROVIDER_BEDROCK)

const providerOptions = computed(() => {
  const list =
    catalog.value?.providers || [
      PROVIDER_OPENAI,
      PROVIDER_BEDROCK,
      PROVIDER_CUSTOM,
    ]
  return list.map((value) => ({ label: value, value }))
})

const regionOptions = computed(() => {
  const list = catalog.value?.bedrock_regions || [
    'us-east-1',
    'us-east-2',
    'us-west-2',
    'eu-west-1',
    'eu-central-1',
    'ap-southeast-1',
    'ap-northeast-1',
  ]
  return list.map((value) => ({ label: value, value }))
})

const bedrockModelOptions = computed(() => {
  const list = catalog.value?.bedrock_models || [
    'openai.gpt-oss-20b-1:0',
    'openai.gpt-oss-120b-1:0',
  ]
  const opts = list.map((value) => ({ label: value, value }))
  if (form.model && !list.includes(form.model)) {
    opts.unshift({ label: form.model, value: form.model })
  }
  return opts
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const [doc, cat] = await Promise.all([
      call('frappe.client.get', {
        doctype: 'CRM AI Settings',
        name: 'CRM AI Settings',
      }),
      call('crm.ai.chat.get_provider_catalog').catch(() => null),
    ])
    catalog.value = cat
    Object.assign(form, {
      enabled: !!doc.enabled,
      provider: doc.provider || PROVIDER_OPENAI,
      aws_region: doc.aws_region || 'us-east-1',
      base_url: doc.base_url || form.base_url,
      model: doc.model || form.model,
      api_key: '',
      credits_per_request: doc.credits_per_request ?? 1,
      default_grant: doc.default_grant ?? 0,
      allow_offline_demo: !!doc.allow_offline_demo,
    })
    if (form.provider === PROVIDER_BEDROCK) {
      form.base_url = bedrockBaseUrl(form.aws_region)
    }
  } catch (e) {
    toast.error(e?.message || __('Could not load AI settings'))
  } finally {
    loading.value = false
  }
}

function onProviderChange(provider) {
  Object.assign(form, applyProviderPreset({ ...form }, provider))
}

function onRegionChange(region) {
  form.aws_region = region
  if (form.provider === PROVIDER_BEDROCK) {
    form.base_url = bedrockBaseUrl(region)
  }
}

async function saveSettings() {
  saving.value = true
  try {
    if (form.provider === PROVIDER_BEDROCK) {
      form.base_url = bedrockBaseUrl(form.aws_region)
    }
    const values = {
      enabled: form.enabled ? 1 : 0,
      provider: form.provider,
      aws_region: form.aws_region,
      base_url: form.base_url,
      model: form.model,
      credits_per_request: Number(form.credits_per_request) || 1,
      default_grant: Number(form.default_grant) || 0,
      allow_offline_demo: form.allow_offline_demo ? 1 : 0,
    }
    if (form.api_key) values.api_key = form.api_key
    await call('frappe.client.set_value', {
      doctype: 'CRM AI Settings',
      name: 'CRM AI Settings',
      fieldname: values,
    })
    toast.success(__('AI settings saved'))
    form.api_key = ''
  } catch (e) {
    toast.error(e?.message || __('Could not save'))
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  try {
    if (form.api_key) {
      await saveSettings()
    }
    const res = await call('crm.ai.chat.test_ai_connection')
    toast.success(
      `${__('Connected')}: ${res.provider} · ${res.model}`,
    )
  } catch (e) {
    toast.error(
      e?.messages?.join?.(' ') || e?.message || __('Connection test failed'),
    )
  } finally {
    testing.value = false
  }
}
</script>
