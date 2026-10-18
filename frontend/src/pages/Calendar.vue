<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Button
          variant="solid"
          :label="__('Schedule')"
          iconLeft="lucide-plus"
          @click="openScheduleDialog"
        />
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 flex-col px-3 pb-3 pt-1 sm:px-5 sm:pb-5">
      <Calendar
        class="min-h-0 flex-1"
        :events="calendarEvents"
        :loading="events.loading"
        :config="calendarConfig"
        @create="onCreate"
        @update="onUpdate"
        @delete="onDelete"
        @rangeChange="onRangeChange"
      >
        <template
          #header="{
            currentMonthYear,
            enabledModes,
            activeView,
            decrement,
            increment,
            updateActiveView,
            setCalendarDate,
            onMonthYearChange,
            selectedMonthDate,
          }"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <DatePicker
              :modelValue="selectedMonthDate"
              :clearable="false"
              @update:modelValue="onMonthYearChange"
            >
              <template #trigger="{ open, setOpen }">
                <Button
                  variant="ghost"
                  class="text-lg-medium text-ink-gray-7"
                  :label="currentMonthYear"
                  iconRight="lucide-chevron-down"
                  @click="setOpen(!open)"
                />
              </template>
            </DatePicker>
            <div class="flex items-center gap-x-1">
              <Button
                variant="ghost"
                icon="lucide-chevron-left"
                @click="decrement"
              />
              <Button
                variant="ghost"
                :label="__('Today')"
                @click="setCalendarDate()"
              />
              <Button
                variant="ghost"
                icon="lucide-chevron-right"
                @click="increment"
              />
              <Dropdown
                :options="viewMenuOptions(enabledModes, updateActiveView)"
              >
                <Button
                  class="ml-1"
                  variant="subtle"
                  :label="__(activeView)"
                  iconRight="lucide-chevron-down"
                />
              </Dropdown>
            </div>
          </div>
        </template>
      </Calendar>
    </div>

    <Dialog v-model="showSchedule" :options="{ title: __('Schedule meeting') }">
      <template #body-content>
        <div class="flex flex-col gap-3">
          <FormControl
            v-model="draft.title"
            type="text"
            :label="__('Title')"
            :placeholder="__('Call with Jane Doe')"
          />
          <FormControl
            v-model="draft.date"
            type="date"
            :label="__('Date')"
            required
          />
          <div class="grid grid-cols-2 gap-3">
            <FormControl
              v-model="draft.fromTime"
              type="time"
              :label="__('Starts')"
              :disabled="draft.isFullDay"
            />
            <FormControl
              v-model="draft.toTime"
              type="time"
              :label="__('Ends')"
              :disabled="draft.isFullDay"
            />
          </div>
          <FormControl
            v-model="draft.venue"
            type="text"
            :label="__('Location / meeting link')"
            :placeholder="__('Zoom, Google Meet, or office')"
          />
          <FormControl
            v-model="draft.isFullDay"
            type="checkbox"
            :label="__('All day')"
          />
          <ErrorMessage v-if="draftError" :message="draftError" />
        </div>
      </template>
      <template #actions>
        <div class="flex flex-row-reverse gap-2">
          <Button
            variant="solid"
            :label="__('Schedule')"
            :loading="saving"
            @click="submitSchedule"
          />
          <Button
            variant="subtle"
            :label="__('Cancel')"
            @click="showSchedule = false"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import {
  Breadcrumbs,
  Button,
  DatePicker,
  Dialog,
  Dropdown,
  ErrorMessage,
  FormControl,
  call,
  createListResource,
  dayjsLocal,
  toast,
} from 'frappe-ui'
import { Calendar } from 'frappe-ui/experimental'
import { computed, reactive, ref } from 'vue'

const breadcrumbs = [{ label: __('Calendar'), route: { name: 'Calendar' } }]

const CALENDAR_COLORS = [
  'amber',
  'violet',
  'pink',
  'cyan',
  'blue',
  'orange',
  'green',
]

const calendarConfig = {
  defaultMode: 'Month',
  isEditMode: true,
  enableShortcuts: true,
  scrollToHour: 9,
  timeFormat: '12h',
  weekends: ['saturday', 'sunday'],
}

const range = ref({ startDate: '', endDate: '' })
const showSchedule = ref(false)
const saving = ref(false)
const draftError = ref('')

const draft = reactive({
  title: '',
  date: '',
  fromTime: '09:00',
  toTime: '10:00',
  venue: '',
  isFullDay: false,
})

const events = createListResource({
  doctype: 'Event',
  fields: [
    'name',
    'subject',
    'starts_on',
    'ends_on',
    'all_day',
    'status',
    'event_type',
    'location',
    'color',
    'description',
  ],
  filters: {
    status: ['!=', 'Cancelled'],
  },
  orderBy: 'starts_on asc',
  pageLength: 500,
  auto: false,
})

const calendarEvents = computed(() =>
  (events.data || []).map(toCalendarEvent).filter(Boolean),
)

function viewMenuOptions(enabledModes, updateActiveView) {
  return (enabledModes || []).map((mode) => ({
    label: __(mode.label),
    icon: mode.iconLeft,
    onClick: () => updateActiveView(mode.value),
  }))
}

function normalizeColor(color) {
  if (!color) return 'green'
  const key = String(color).toLowerCase()
  if (CALENDAR_COLORS.includes(key)) return key
  return 'green'
}

function toCalendarEvent(doc) {
  if (!doc?.starts_on) return null
  const start = dayjsLocal(doc.starts_on)
  const end = dayjsLocal(doc.ends_on || doc.starts_on)
  const isFullDay = !!doc.all_day
  return {
    id: doc.name,
    title: doc.subject || __('(No title)'),
    fromDate: start.format('YYYY-MM-DD'),
    toDate: end.format('YYYY-MM-DD'),
    fromTime: isFullDay ? '' : start.format('HH:mm'),
    toTime: isFullDay ? '' : end.format('HH:mm'),
    isFullDay,
    venue: doc.location || '',
    color: normalizeColor(doc.color),
    type: doc.event_type || 'Public',
  }
}

function eventPayload(event) {
  const fromDate = event.fromDate || event.date
  const toDate = event.toDate || fromDate
  const isFullDay = !!event.isFullDay
  // Color stays on the calendar UI only — Frappe Event color options vary by version.
  if (isFullDay) {
    return {
      subject: event.title || __('Untitled meeting'),
      starts_on: `${fromDate} 00:00:00`,
      ends_on: `${toDate} 23:59:59`,
      all_day: 1,
      location: event.venue || '',
      event_type: event.type || 'Public',
      status: 'Open',
    }
  }
  const ft = (event.fromTime || '09:00').slice(0, 5)
  const tt = (event.toTime || '10:00').slice(0, 5)
  return {
    subject: event.title || __('Untitled meeting'),
    starts_on: `${fromDate} ${ft}:00`,
    ends_on: `${toDate} ${tt}:00`,
    all_day: 0,
    location: event.venue || '',
    event_type: event.type || 'Public',
    status: 'Open',
  }
}

function isTempId(id) {
  return !id || String(id).startsWith('#')
}

async function reloadInRange() {
  if (!range.value.startDate || !range.value.endDate) return
  events.filters = {
    status: ['!=', 'Cancelled'],
    starts_on: [
      'between',
      [`${range.value.startDate} 00:00:00`, `${range.value.endDate} 23:59:59`],
    ],
  }
  await events.reload()
}

function onRangeChange({ startDate, endDate }) {
  range.value = { startDate, endDate }
  reloadInRange()
}

async function persistCreate(event) {
  await call('frappe.client.insert', {
    doc: {
      doctype: 'Event',
      ...eventPayload(event),
    },
  })
}

async function onCreate(event) {
  try {
    await persistCreate(event)
    toast.success(__('Meeting scheduled'))
    await reloadInRange()
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not create meeting'),
    )
    await reloadInRange()
  }
}

async function onUpdate(event) {
  if (isTempId(event.id)) {
    await onCreate(event)
    return
  }
  try {
    await call('frappe.client.set_value', {
      doctype: 'Event',
      name: event.id,
      fieldname: eventPayload(event),
    })
    await reloadInRange()
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not update meeting'),
    )
    await reloadInRange()
  }
}

async function onDelete(eventId) {
  if (isTempId(eventId)) return
  try {
    await call('frappe.client.delete', {
      doctype: 'Event',
      name: eventId,
    })
    toast.success(__('Meeting deleted'))
    await reloadInRange()
  } catch (e) {
    toast.error(
      e?.messages?.[0] || e?.message || __('Could not delete meeting'),
    )
    await reloadInRange()
  }
}

function openScheduleDialog() {
  const start = dayjsLocal().add(1, 'hour').startOf('hour')
  draft.title = ''
  draft.date = start.format('YYYY-MM-DD')
  draft.fromTime = start.format('HH:mm')
  draft.toTime = start.add(1, 'hour').format('HH:mm')
  draft.venue = ''
  draft.isFullDay = false
  draftError.value = ''
  showSchedule.value = true
}

async function submitSchedule() {
  draftError.value = ''
  if (!draft.date) {
    draftError.value = __('Date is required')
    return
  }
  if (!draft.isFullDay && (!draft.fromTime || !draft.toTime)) {
    draftError.value = __('Start and end time are required')
    return
  }
  if (!draft.isFullDay && draft.fromTime >= draft.toTime) {
    draftError.value = __('Start time must be before end time')
    return
  }
  saving.value = true
  try {
    await persistCreate({
      title: draft.title || __('New meeting'),
      fromDate: draft.date,
      toDate: draft.date,
      fromTime: draft.fromTime,
      toTime: draft.toTime,
      isFullDay: draft.isFullDay,
      venue: draft.venue,
      color: 'blue',
    })
    toast.success(__('Meeting scheduled'))
    showSchedule.value = false
    await reloadInRange()
  } catch (e) {
    draftError.value =
      e?.messages?.[0] || e?.message || __('Could not create meeting')
  } finally {
    saving.value = false
  }
}
</script>
