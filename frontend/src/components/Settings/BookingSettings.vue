<template>
  <SettingsLayoutBase
    :title="__('Booking')"
    :description="
      __(
        'Connect your Google Calendar, Google Meet, or Zoom. Each agent connects their own account.',
      )
    "
  >
    <template #header-actions>
      <Button
        variant="solid"
        :label="__('Save')"
        :loading="saving"
        @click="save"
      />
    </template>
    <template #content>
      <div v-if="loading" class="flex justify-center py-12">
        <LoadingIndicator class="w-4" />
      </div>
      <div v-else class="max-w-xl">
        <p
          v-if="!profile?.appointment_installed"
          class="mb-6 text-p-sm text-ink-gray-6"
        >
          {{
            __(
              'Install the frappe_appointment app on this site to enable native booking with Meet and Zoom.',
            )
          }}
        </p>

        <div class="text-base-semibold text-ink-gray-9">
          {{ __('Video for bookings') }}
        </div>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{
            __(
              'Pick a provider and paste your personal link, or connect Google Calendar for auto Meet links.',
            )
          }}
        </p>
        <div class="mt-6 space-y-4">
          <FormControl
            v-model="form.meeting_provider"
            type="select"
            :label="__('Meeting provider')"
            :options="meetingProviderOptions"
          />
          <FormControl
            v-if="form.meeting_provider === 'Google Meet'"
            v-model="form.meet_personal_url"
            type="text"
            :label="__('Google Meet link')"
            :placeholder="__('https://meet.google.com/…')"
          />
          <FormControl
            v-if="form.meeting_provider === 'Zoom'"
            v-model="form.zoom_personal_url"
            type="text"
            :label="__('Zoom personal meeting URL')"
            :placeholder="__('https://zoom.us/j/…')"
          />
          <FormControl
            v-if="form.meeting_provider === 'Zoom'"
            v-model="form.zoom_account_email"
            type="email"
            :label="__('Zoom account email')"
            :placeholder="__('you@agency.com')"
          />
        </div>

        <template v-if="calendarStatus?.can_configure_api">
          <div class="mt-10 text-base-semibold text-ink-gray-9">
            {{ __('Google API') }}
          </div>
          <p class="mt-1 text-p-sm text-ink-gray-6">
            {{
              __(
                'One-time site setup: OAuth client from Google Cloud. After this, every agent can connect their own calendar.',
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
                calendarStatus?.has_client_secret
                  ? __('•••••••• (saved — leave blank to keep)')
                  : ''
              "
            />
            <FormControl
              :model-value="calendarStatus?.redirect_uri || ''"
              type="text"
              :label="__('Authorized redirect URI')"
              readonly
            />
            <Button
              variant="solid"
              :label="__('Save Google API')"
              :loading="savingApi"
              @click="saveApi"
            />
          </div>
        </template>

        <div class="mt-10 text-base-semibold text-ink-gray-9">
          <span class="inline-flex items-center gap-2">
            {{ __('Your Google Calendar') }}
            <Badge
              :label="calendarBadge.label"
              :theme="calendarBadge.theme"
              variant="subtle"
              size="sm"
            />
          </span>
        </div>
        <p class="mt-1 text-p-sm text-ink-gray-6">
          {{
            __(
              'Connect to sync busy times and (optionally) auto-create Google Meet links.',
            )
          }}
        </p>

        <p
          v-if="!canConnectCalendar"
          class="mt-6 text-p-sm text-ink-gray-6"
        >
          {{
            calendarStatus?.can_configure_api
              ? __(
                  'Save Google API credentials above, then connect your calendar here.',
                )
              : __(
                  'Ask a Sales Manager to add Google API credentials once. You can still use Meet or Zoom personal links above.',
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
                calendarStatus?.calendar?.connected
                  ? __('Reconnect Google')
                  : __('Connect Google')
              "
              :loading="authorizing"
              @click="authorize"
            />
            <Button
              v-if="calendarStatus?.calendar?.connected"
              variant="subtle"
              :label="__('Sync now')"
              :loading="syncing"
              @click="syncNow"
            />
          </div>
        </div>

        <template v-if="form.zoom_site?.can_configure">
          <div class="mt-10 text-base-semibold text-ink-gray-9">
            {{ __('Zoom API (optional)') }}
          </div>
          <p class="mt-1 text-p-sm text-ink-gray-6">
            {{
              __(
                'Server-to-Server OAuth creates a unique Zoom link per booking. Agents can use a personal Zoom URL instead.',
              )
            }}
          </p>
          <div class="mt-6 space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-base-medium text-ink-gray-8">{{
                __('Enable Zoom API')
              }}</span>
              <Switch v-model="zoomSiteForm.enable_zoom" size="sm" />
            </div>
            <FormControl
              v-model="zoomSiteForm.zoom_account_id"
              type="text"
              :label="__('Account ID')"
            />
            <FormControl
              v-model="zoomSiteForm.zoom_client_id"
              type="text"
              :label="__('Client ID')"
            />
            <FormControl
              v-model="zoomSiteForm.zoom_client_secret"
              type="password"
              :label="__('Client Secret')"
              :placeholder="
                form.zoom_site?.has_client_secret
                  ? __('•••••••• (saved — leave blank to keep)')
                  : ''
              "
            />
            <Button
              variant="subtle"
              :label="__('Save Zoom API')"
              :loading="savingZoomSite"
              @click="saveZoomSite"
            />
          </div>
        </template>

        <p class="mt-10 text-p-sm text-ink-gray-6">
          {{ __('Configure your public booking page under') }}
          <button
            type="button"
            class="text-ink-gray-8 underline"
            @click="goBookingPage"
          >
            {{ __('Booking') }}
          </button>
          .
        </p>
      </div>
    </template>
  </SettingsLayoutBase>
</template>

<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import { showSettings } from '@/composables/settings'
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
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const savingApi = ref(false)
const savingConnection = ref(false)
const savingZoomSite = ref(false)
const authorizing = ref(false)
const syncing = ref(false)
const calendarStatus = ref(null)
const profile = ref(null)

const meetingProviderOptions = [
  { label: __('None'), value: 'None' },
  { label: __('Google Meet'), value: 'Google Meet' },
  { label: __('Zoom'), value: 'Zoom' },
]

const form = reactive({
  meeting_provider: 'None',
  zoom_personal_url: '',
  meet_personal_url: '',
  zoom_account_email: '',
  enabled: false,
  provider: 'Native',
  page_title: '',
  slug: '',
  duration_minutes: 30,
  timezone: 'UTC',
  advance_days: 14,
  buffer_minutes: 0,
  calendly_url: '',
  availability_json: '',
  zoom_site: null,
})

const apiForm = reactive({
  enable: true,
  client_id: '',
  client_secret: '',
})

const zoomSiteForm = reactive({
  enable_zoom: false,
  zoom_account_id: '',
  zoom_client_id: '',
  zoom_client_secret: '',
})

const connectionForm = reactive({
  calendar_name: '',
  pull_from_google_calendar: true,
  push_to_google_calendar: true,
})

const canConnectCalendar = computed(
  () =>
    Boolean(calendarStatus.value?.api_enabled) &&
    Boolean(calendarStatus.value?.has_client_id) &&
    Boolean(calendarStatus.value?.has_client_secret),
)

const calendarBadge = computed(() => {
  if (calendarStatus.value?.calendar?.connected) {
    return { label: __('Connected'), theme: 'green' }
  }
  if (!canConnectCalendar.value) {
    return { label: __('API setup needed'), theme: 'orange' }
  }
  return { label: __('Not connected'), theme: 'gray' }
})

function applyProfile(data) {
  profile.value = data
  if (!data) return
  form.meeting_provider = data.meeting_provider || 'None'
  form.zoom_personal_url = data.zoom_personal_url || ''
  form.meet_personal_url = data.meet_personal_url || ''
  form.zoom_account_email = data.zoom_account_email || ''
  form.enabled = !!data.enabled
  form.provider = data.provider || 'Native'
  form.page_title = data.page_title || ''
  form.slug = data.slug || ''
  form.duration_minutes = data.duration_minutes || 30
  form.timezone = data.timezone || 'UTC'
  form.advance_days = data.advance_days || 14
  form.buffer_minutes = data.buffer_minutes || 0
  form.calendly_url = data.calendly_url || ''
  form.availability_json =
    data.availability_json || JSON.stringify(data.availability || {})
  form.zoom_site = data.zoom_site || null
  if (data.zoom_site?.can_configure) {
    zoomSiteForm.enable_zoom = !!data.zoom_site.enable_zoom
    zoomSiteForm.zoom_account_id = data.zoom_site.zoom_account_id || ''
    zoomSiteForm.zoom_client_id = data.zoom_site.zoom_client_id || ''
  }
}

function applyCalendar(data) {
  calendarStatus.value = data
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
  }
}

async function load() {
  loading.value = true
  try {
    const [data, calendar] = await Promise.all([
      call('crm.api.booking.get_my_booking_profile'),
      call('crm.api.calendar.get_google_calendar_status'),
    ])
    applyProfile(data)
    applyCalendar(calendar)
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not load booking settings'),
    )
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const data = await call('crm.api.booking.save_my_booking_profile', {
      enabled: form.enabled ? 1 : 0,
      provider: form.provider,
      page_title: form.page_title,
      slug: form.slug,
      duration_minutes: form.duration_minutes,
      timezone: form.timezone,
      advance_days: form.advance_days,
      buffer_minutes: form.buffer_minutes,
      calendly_url: form.calendly_url,
      availability_json: form.availability_json,
      meeting_provider: form.meeting_provider,
      zoom_personal_url: form.zoom_personal_url,
      meet_personal_url: form.meet_personal_url,
      zoom_account_email: form.zoom_account_email,
    })
    applyProfile(data)
    toast.success(__('Booking integrations saved'))
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not save booking settings'),
    )
  } finally {
    saving.value = false
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
    applyCalendar(data)
    toast.success(__('Google API settings saved'))
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not save Google settings'),
    )
  } finally {
    savingApi.value = false
  }
}

async function saveZoomSite() {
  savingZoomSite.value = true
  try {
    const result = await call('crm.api.booking.save_zoom_site_settings', {
      enable_zoom: zoomSiteForm.enable_zoom ? 1 : 0,
      zoom_account_id: zoomSiteForm.zoom_account_id,
      zoom_client_id: zoomSiteForm.zoom_client_id,
      zoom_client_secret: zoomSiteForm.zoom_client_secret || undefined,
    })
    form.zoom_site = result?.zoom_site || form.zoom_site
    zoomSiteForm.zoom_client_secret = ''
    toast.success(__('Zoom API settings saved'))
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not save Zoom settings'),
    )
  } finally {
    savingZoomSite.value = false
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
    applyCalendar(data)
    await load()
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
        reauthorize: calendarStatus.value?.calendar?.connected ? 1 : 0,
      },
    )
    if (result?.url) {
      window.open(result.url, '_blank', 'noopener')
      toast.info(__('Finish authorizing in the Google window, then sync.'))
    } else {
      await load()
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
    if (result?.status) applyCalendar(result.status)
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

function goBookingPage() {
  showSettings.value = false
  router.push({ name: 'Booking' })
}

onMounted(load)
</script>
