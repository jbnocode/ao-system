<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Button
          variant="solid"
          :label="__('Save')"
          :loading="saving"
          @click="save"
        />
      </template>
    </LayoutHeader>

    <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-8">
      <div v-if="loading" class="flex justify-center py-16">
        <LoadingIndicator class="w-4" />
      </div>

      <div v-else class="mx-auto max-w-xl text-ink-gray-8">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-base-semibold text-ink-gray-9">
              {{ __('Booking page') }}
            </div>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ __('Share a link so prospects can book time with you.') }}
            </p>
          </div>
          <Switch v-model="form.enabled" size="sm" />
        </div>

        <div
          v-if="shareUrl"
          class="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center"
        >
          <div class="min-w-0 flex-1 truncate text-p-sm text-ink-gray-7">
            {{ shareUrl }}
          </div>
          <div class="flex shrink-0 gap-2">
            <Button variant="subtle" :label="__('Copy')" @click="copyShare" />
            <Button variant="subtle" :label="__('Open')" @click="openShare" />
          </div>
        </div>

        <div class="mt-10 text-base-semibold text-ink-gray-9">
          {{ __('Page details') }}
        </div>
        <div class="mt-6 space-y-4">
          <FormControl
            v-model="form.provider"
            type="select"
            :label="__('Scheduling provider')"
            :options="providerOptions"
          />
          <FormControl
            v-model="form.page_title"
            type="text"
            :label="__('Title')"
            :placeholder="__('Meet with Jane')"
          />
          <FormControl
            v-model="form.slug"
            type="text"
            :label="__('Slug')"
            :placeholder="__('jane-doe')"
          />
          <p class="text-p-sm text-ink-gray-5 -mt-2">
            {{ __('Public path') }}:
            <span class="text-ink-gray-7"
              >/crm/book/{{ form.slug || '…' }}</span
            >
          </p>
          <FormControl
            v-model="form.duration_minutes"
            type="number"
            :label="__('Duration (minutes)')"
          />
          <div class="flex items-center justify-between gap-4">
            <div class="flex flex-col gap-1">
              <span class="text-base-medium text-ink-gray-8">
                {{ __('Timezone') }}
              </span>
              <span class="text-p-sm text-ink-gray-6">
                {{ __('Timezone used for your availability.') }}
              </span>
            </div>
            <Combobox
              v-model="form.timezone"
              class="w-52"
              :options="timezoneOptions"
            />
          </div>
        </div>

        <div class="mt-10 flex items-start justify-between gap-3">
          <div>
            <div class="text-base-semibold text-ink-gray-9">
              {{ __('Video meeting') }}
            </div>
            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ videoSummary }}
            </p>
          </div>
          <Badge
            :label="form.meeting_provider || __('None')"
            theme="gray"
            variant="subtle"
            size="sm"
          />
        </div>
        <Button
          class="mt-4"
          variant="subtle"
          :label="__('Manage integrations')"
          @click="openBookingSettings"
        />

        <template v-if="form.provider === 'Calendly'">
          <div class="mt-10 text-base-semibold text-ink-gray-9">
            {{ __('Calendly') }}
          </div>
          <div class="mt-6">
            <FormControl
              v-model="form.calendly_url"
              type="text"
              :label="__('Calendly link')"
              :placeholder="__('https://calendly.com/you/30min')"
            />
          </div>
        </template>

        <template v-if="form.provider === 'Native'">
          <div class="mt-10 flex flex-wrap items-end justify-between gap-3">
            <div class="text-base-semibold text-ink-gray-9">
              {{ __('Weekly availability') }}
            </div>
            <FormControl
              v-model="form.advance_days"
              type="number"
              class="w-28"
              :label="__('Days ahead')"
            />
          </div>
          <div class="mt-4 flex flex-col">
            <div
              v-for="day in weekdays"
              :key="day.key"
              class="flex flex-wrap items-center gap-2 border-b border-outline-gray-modals py-2.5 last:border-0"
            >
              <div class="w-12 shrink-0 text-p-sm-medium text-ink-gray-7">
                {{ day.label }}
              </div>
              <Switch
                :model-value="isDayOn(day.key)"
                size="sm"
                @update:model-value="(v) => toggleDay(day.key, v)"
              />
              <template v-if="isDayOn(day.key)">
                <FormControl
                  :model-value="dayWindow(day.key)[0]"
                  type="time"
                  class="w-32"
                  @update:model-value="(v) => setDayWindow(day.key, 0, v)"
                />
                <span class="text-p-sm text-ink-gray-5">{{ __('to') }}</span>
                <FormControl
                  :model-value="dayWindow(day.key)[1]"
                  type="time"
                  class="w-32"
                  @update:model-value="(v) => setDayWindow(day.key, 1, v)"
                />
              </template>
              <span v-else class="text-p-sm text-ink-gray-5">
                {{ __('Unavailable') }}
              </span>
            </div>
          </div>
          <FormControl
            v-model="form.buffer_minutes"
            type="number"
            class="mt-4 w-40"
            :label="__('Buffer (minutes)')"
          />
        </template>

        <div class="mt-10 text-base-semibold text-ink-gray-9">
          {{ __('Recent bookings') }}
        </div>
        <div
          v-if="bookings.loading && !bookings.data?.length"
          class="flex justify-center py-8"
        >
          <LoadingIndicator class="w-4" />
        </div>
        <div
          v-else-if="!bookings.data?.length"
          class="mt-4 text-p-sm text-ink-gray-5"
        >
          {{ __('No bookings yet.') }}
        </div>
        <div v-else class="mt-2 flex flex-col">
          <div
            v-for="row in bookings.data"
            :key="row.name"
            class="flex items-start justify-between gap-3 border-b border-outline-gray-modals py-3 last:border-0"
          >
            <div class="min-w-0">
              <div class="truncate text-p-sm-medium text-ink-gray-8">
                {{ row.guest_name }}
              </div>
              <div class="text-p-sm text-ink-gray-5">
                {{ formatWhen(row.starts_on) }}
                <span
                  v-if="
                    row.meeting_provider && row.meeting_provider !== 'None'
                  "
                >
                  · {{ row.meeting_provider }}
                </span>
              </div>
            </div>
            <Badge
              :label="__(row.status)"
              :theme="row.status === 'Scheduled' ? 'blue' : 'gray'"
              variant="subtle"
              size="sm"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import {
  showSettings,
  activeSettingsPage,
} from '@/composables/settings'
import {
  Badge,
  Breadcrumbs,
  Button,
  Combobox,
  FormControl,
  LoadingIndicator,
  Switch,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, onMounted, reactive, ref } from 'vue'

const loading = ref(true)
const saving = ref(false)

const breadcrumbs = [{ label: __('Booking'), route: { name: 'Booking' } }]

const weekdays = [
  { key: 'mon', label: __('Mon') },
  { key: 'tue', label: __('Tue') },
  { key: 'wed', label: __('Wed') },
  { key: 'thu', label: __('Thu') },
  { key: 'fri', label: __('Fri') },
  { key: 'sat', label: __('Sat') },
  { key: 'sun', label: __('Sun') },
]

const providerOptions = [
  { label: __('Native'), value: 'Native' },
  { label: __('Calendly'), value: 'Calendly' },
]

const form = reactive({
  enabled: false,
  provider: 'Native',
  page_title: '',
  slug: '',
  duration_minutes: 30,
  timezone: 'UTC',
  advance_days: 14,
  buffer_minutes: 0,
  calendly_url: '',
  meeting_provider: 'None',
  zoom_personal_url: '',
  meet_personal_url: '',
  zoom_account_email: '',
  google_calendar_connected: false,
  availability: {
    mon: [['09:00', '17:00']],
    tue: [['09:00', '17:00']],
    wed: [['09:00', '17:00']],
    thu: [['09:00', '17:00']],
    fri: [['09:00', '17:00']],
    sat: [],
    sun: [],
  },
  public_url: '',
  share_url: '',
  schedule_url: '',
  appointment_installed: false,
})

const bookings = createResource({
  url: 'crm.api.booking.get_my_recent_bookings',
  auto: false,
})

const timeZones = createResource({
  url: 'frappe.core.doctype.user.user.get_timezones',
  cache: 'TimeZones',
  auto: true,
})

const timezoneOptions = computed(
  () =>
    timeZones.data?.timezones?.map((tz) => ({ label: tz, value: tz })) || [],
)

const shareUrl = computed(() => {
  if (form.provider === 'Calendly' && form.calendly_url) {
    return form.calendly_url
  }
  return form.schedule_url || form.share_url || form.public_url || ''
})

const videoSummary = computed(() => {
  if (form.meeting_provider === 'Google Meet') {
    if (form.google_calendar_connected) {
      return __('Google Meet via your connected Google Calendar.')
    }
    return form.meet_personal_url
      ? __('Google Meet personal link is set.')
      : __('Add a Meet link or connect Google Calendar in Booking settings.')
  }
  if (form.meeting_provider === 'Zoom') {
    return form.zoom_personal_url
      ? __('Zoom personal meeting link is connected.')
      : __('Add your Zoom link in Booking settings.')
  }
  return __('No video provider selected. Configure in Booking settings.')
})

function isDayOn(key) {
  return (form.availability[key] || []).length > 0
}

function dayWindow(key) {
  const windows = form.availability[key] || []
  return windows[0] || ['09:00', '17:00']
}

function toggleDay(key, on) {
  form.availability[key] = on ? [['09:00', '17:00']] : []
}

function setDayWindow(key, index, value) {
  const current = dayWindow(key)
  const next = [...current]
  next[index] = (value || '').slice(0, 5)
  form.availability[key] = [next]
}

function applyProfile(data) {
  if (!data) return
  form.enabled = !!data.enabled
  form.provider = data.provider || 'Native'
  form.page_title = data.page_title || ''
  form.slug = data.slug || ''
  form.duration_minutes = data.duration_minutes || 30
  form.timezone = data.timezone || 'UTC'
  form.advance_days = data.advance_days || 14
  form.buffer_minutes = data.buffer_minutes || 0
  form.calendly_url = data.calendly_url || ''
  form.meeting_provider = data.meeting_provider || 'None'
  form.zoom_personal_url = data.zoom_personal_url || ''
  form.meet_personal_url = data.meet_personal_url || ''
  form.zoom_account_email = data.zoom_account_email || ''
  form.google_calendar_connected = !!data.google_calendar_connected
  form.public_url = data.public_url || ''
  form.share_url = data.share_url || ''
  form.schedule_url = data.schedule_url || ''
  form.appointment_installed = !!data.appointment_installed
  if (data.availability && typeof data.availability === 'object') {
    form.availability = { ...form.availability, ...data.availability }
  }
}

async function load() {
  loading.value = true
  try {
    const data = await call('crm.api.booking.get_my_booking_profile')
    applyProfile(data)
    await bookings.fetch()
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not load booking page'),
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
      availability_json: JSON.stringify(form.availability),
      meeting_provider: form.meeting_provider,
      zoom_personal_url: form.zoom_personal_url,
      meet_personal_url: form.meet_personal_url,
      zoom_account_email: form.zoom_account_email,
    })
    applyProfile(data)
    toast.success(__('Booking page saved'))
    await bookings.fetch()
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not save booking page'),
    )
  } finally {
    saving.value = false
  }
}

async function copyShare() {
  const url = shareUrl.value
  if (!url) {
    toast.error(__('Save and enable booking first'))
    return
  }
  try {
    await navigator.clipboard.writeText(url)
    toast.success(__('Link copied'))
  } catch {
    toast.error(__('Could not copy link'))
  }
}

function openShare() {
  const url = shareUrl.value
  if (!url) return
  window.open(url, '_blank', 'noopener')
}

function openBookingSettings() {
  activeSettingsPage.value = 'Booking'
  showSettings.value = true
}

function formatWhen(value) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

onMounted(load)
</script>
