<template>
  <SettingsLayoutBase
    :title="__('Calendar')"
    :description="
      __(
        'Connect Google Calendar so meetings sync both ways with your CRM calendar.',
      )
    "
  >
    <template #header-actions>
      <Button
        v-if="status?.docs_url"
        variant="subtle"
        icon-left="lucide-external-link"
        :label="__('Docs')"
        @click="openDocs"
      />
    </template>
    <template #content>
      <div v-if="loading" class="flex justify-center py-12">
        <LoadingIndicator class="w-4" />
      </div>
      <div v-else class="max-w-xl">
        <template v-if="status?.can_configure_api">
          <div class="text-base-semibold text-ink-gray-9">
            {{ __('Google API') }}
          </div>
          <p class="mt-1 text-p-sm text-ink-gray-6">
            {{
              __(
                'Create an OAuth client in Google Cloud, enable the Calendar API, then paste the credentials here.',
              )
            }}
          </p>
          <div class="mt-6 space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-base-medium text-ink-gray-8">{{
                __('Enabled')
              }}</span>
              <Switch v-model="apiForm.enable" size="sm" />
            </div>
            <FormControl
              v-model="apiForm.client_id"
              type="text"
              :label="__('Client ID')"
              :placeholder="__('xxxx.apps.googleusercontent.com')"
            />
            <FormControl
              v-model="apiForm.client_secret"
              type="password"
              :label="__('Client Secret')"
              :placeholder="
                status?.has_client_secret
                  ? __('•••••••• (saved — leave blank to keep)')
                  : ''
              "
            />
            <FormControl
              :model-value="status?.redirect_uri || ''"
              type="text"
              :label="__('Authorized redirect URI')"
              readonly
            />
            <p class="text-p-sm text-ink-gray-5 -mt-2">
              {{
                __(
                  'Add this exact URI under Authorized redirect URIs in Google Cloud Console.',
                )
              }}
            </p>
            <Button
              variant="solid"
              :label="__('Save Google API')"
              :loading="savingApi"
              @click="saveApi"
            />
          </div>
        </template>

        <div
          class="text-base-semibold text-ink-gray-9"
          :class="status?.can_configure_api ? 'mt-10' : ''"
        >
          <span class="inline-flex items-center gap-2">
            {{ __('Your calendar') }}
            <Badge
              :label="connectionBadge.label"
              :theme="connectionBadge.theme"
              variant="subtle"
              size="sm"
            />
          </span>
        </div>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{ connectionHelp }}
        </p>

        <p
          v-if="!canConnect"
          class="mt-6 text-p-sm text-ink-gray-6"
        >
          {{
            status?.can_configure_api
              ? __(
                  'Enable Google API above and save a Client ID and Client Secret first. Then you can connect your calendar.',
                )
              : __(
                  'Ask a Sales Manager to add Google API credentials once. After that you can connect your own calendar here.',
                )
          }}
        </p>

        <div v-else class="mt-6 space-y-4">
          <FormControl
            v-model="connectionForm.calendar_name"
            type="text"
            :label="__('Calendar name')"
            :placeholder="__('My CRM Calendar')"
          />
          <div class="flex items-center justify-between">
            <span class="text-base-medium text-ink-gray-8">
              {{ __('Pull from Google') }}
            </span>
            <Switch
              v-model="connectionForm.pull_from_google_calendar"
              size="sm"
            />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-base-medium text-ink-gray-8">
              {{ __('Push to Google') }}
            </span>
            <Switch
              v-model="connectionForm.push_to_google_calendar"
              size="sm"
            />
          </div>
          <div class="flex flex-wrap items-center gap-2 pt-1">
            <Button
              variant="subtle"
              :label="__('Save connection')"
              :loading="savingConnection"
              @click="saveConnection"
            />
            <Button
              variant="solid"
              :label="
                status?.calendar?.connected
                  ? __('Reconnect Google')
                  : __('Connect Google')
              "
              :loading="authorizing"
              @click="authorize"
            />
            <Button
              v-if="status?.calendar?.connected"
              variant="subtle"
              :label="__('Sync now')"
              :loading="syncing"
              @click="syncNow"
            />
          </div>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>
</template>

<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import {
  Badge,
  Button,
  FormControl,
  LoadingIndicator,
  Switch,
  call,
  toast,
} from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'

const loading = ref(true)
const savingApi = ref(false)
const savingConnection = ref(false)
const authorizing = ref(false)
const syncing = ref(false)
const status = ref(null)

const apiForm = reactive({
  enable: true,
  client_id: '',
  client_secret: '',
})

const connectionForm = reactive({
  calendar_name: '',
  pull_from_google_calendar: true,
  push_to_google_calendar: true,
})

const canConnect = computed(
  () =>
    Boolean(status.value?.api_enabled) &&
    Boolean(status.value?.has_client_id) &&
    Boolean(status.value?.has_client_secret),
)

const connectionHelp = computed(() => {
  if (status.value?.calendar?.connected) {
    return __('Connected to Google. Events sync with CRM.')
  }
  if (!canConnect.value) {
    return __('Google API must be configured before you can connect.')
  }
  return __('Create a connection, then authorize with Google.')
})

const connectionBadge = computed(() => {
  if (status.value?.calendar?.connected) {
    return { label: __('Connected'), theme: 'green' }
  }
  if (!canConnect.value) {
    return { label: __('Setup required'), theme: 'orange' }
  }
  return { label: __('Not connected'), theme: 'gray' }
})

function applyStatus(data) {
  status.value = data
  if (data?.can_configure_api) {
    apiForm.enable = Boolean(data.api_enabled)
    apiForm.client_id = data.client_id || ''
    apiForm.client_secret = ''
  }
  const cal = data?.calendar
  if (cal) {
    connectionForm.calendar_name = cal.calendar_name || ''
    connectionForm.pull_from_google_calendar = Boolean(
      cal.pull_from_google_calendar,
    )
    connectionForm.push_to_google_calendar = Boolean(
      cal.push_to_google_calendar,
    )
  } else if (!connectionForm.calendar_name) {
    connectionForm.calendar_name = ''
  }
}

async function reload() {
  const data = await call('crm.api.calendar.get_google_calendar_status')
  applyStatus(data)
}

onMounted(async () => {
  try {
    await reload()
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not load calendar settings'),
    )
  } finally {
    loading.value = false
  }
})

function openDocs() {
  if (status.value?.docs_url) {
    window.open(status.value.docs_url, '_blank', 'noopener')
  }
}

async function saveApi() {
  savingApi.value = true
  try {
    const data = await call('crm.api.calendar.save_google_settings', {
      enable: apiForm.enable ? 1 : 0,
      client_id: apiForm.client_id,
      client_secret: apiForm.client_secret || undefined,
    })
    applyStatus(data)
    toast.success(__('Google API settings saved'))
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not save Google settings'),
    )
  } finally {
    savingApi.value = false
  }
}

async function saveConnection() {
  savingConnection.value = true
  try {
    const data = await call('crm.api.calendar.ensure_my_google_calendar', {
      calendar_name: connectionForm.calendar_name,
      pull_from_google_calendar: connectionForm.pull_from_google_calendar
        ? 1
        : 0,
      push_to_google_calendar: connectionForm.push_to_google_calendar ? 1 : 0,
    })
    applyStatus(data)
    toast.success(__('Calendar connection saved'))
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not save connection'),
    )
  } finally {
    savingConnection.value = false
  }
}

async function authorize() {
  authorizing.value = true
  try {
    await call('crm.api.calendar.ensure_my_google_calendar', {
      calendar_name: connectionForm.calendar_name,
      pull_from_google_calendar: connectionForm.pull_from_google_calendar
        ? 1
        : 0,
      push_to_google_calendar: connectionForm.push_to_google_calendar ? 1 : 0,
    })
    const result = await call(
      'crm.api.calendar.authorize_my_google_calendar',
      {
        reauthorize: status.value?.calendar?.connected ? 1 : 0,
      },
    )
    if (result?.url) {
      window.open(result.url, '_blank', 'noopener')
      toast.info(__('Finish authorizing in the Google window, then sync.'))
    } else {
      await reload()
      toast.success(__('Google Calendar authorized'))
    }
  } catch (e) {
    toast.error(
      e?.messages?.[0] ||
        e?.message ||
        __('Could not start Google authorization'),
    )
  } finally {
    authorizing.value = false
  }
}

async function syncNow() {
  syncing.value = true
  try {
    const result = await call('crm.api.calendar.sync_my_google_calendar')
    if (result?.status) applyStatus(result.status)
    const msg = Array.isArray(result?.messages)
      ? result.messages.filter(Boolean).join(' ')
      : ''
    toast.success(msg || __('Calendar synced'))
  } catch (e) {
    toast.error(e?.messages?.[0] || e?.message || __('Sync failed'))
  } finally {
    syncing.value = false
  }
}
</script>
