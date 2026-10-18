<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Button
          variant="subtle"
          :label="__('AI Call')"
          icon-left="lucide-phone-call"
          @click="router.push({ name: 'Dialer' })"
        />
        <Button
          variant="subtle"
          :label="__('Call logs')"
          @click="router.push({ name: 'Dialer', query: { panel: 'call-logs' } })"
        />
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 overflow-hidden bg-surface-white">
      <div
        class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden lg:flex-row"
      >
      <div
        class="flex min-h-0 min-w-0 flex-1 flex-col border-b border-outline-gray-modals lg:border-b-0 lg:border-r"
      >
        <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
          <div class="flex flex-wrap items-center gap-2 px-4 pb-3 pt-3">
            <TabButtons v-model="listTab" :options="listTabOptions" />
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 pb-4">
            <div v-if="listTab === 'recent'">
              <div
                v-if="recent.loading && !recent.data?.length"
                class="flex justify-center py-12"
              >
                <LoadingIndicator class="w-4" />
              </div>
              <div
                v-else-if="!recent.data?.length"
                class="py-10 text-center text-p-sm text-ink-gray-5"
              >
                {{ __('No recent calls.') }}
              </div>
              <div v-else class="flex flex-col">
                <div
                  v-for="row in recent.data"
                  :key="row.name"
                  class="flex w-full items-center justify-between gap-3 border-b border-outline-gray-modals py-3"
                >
                  <button
                    type="button"
                    class="flex min-w-0 flex-1 items-start gap-3 text-left transition hover:opacity-80"
                    @click="selectNumber(dialNumber(row))"
                  >
                    <div
                      class="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
                    >
                      <LucidePhoneIncoming
                        v-if="row.type === 'Incoming'"
                        class="size-4"
                      />
                      <LucidePhoneOutgoing v-else class="size-4" />
                    </div>
                    <div class="min-w-0">
                      <div class="truncate text-p-base-medium text-ink-gray-8">
                        {{ dialNumber(row) || __('Unknown') }}
                      </div>
                      <div class="text-p-sm text-ink-gray-5">
                        {{ row.type }}
                        <span v-if="row.status"> · {{ row.status }}</span>
                        · {{ formatDate(row.creation, '', true, true) }}
                        <span v-if="row.ai_transcript">
                          · {{ __('Transcript') }}
                        </span>
                      </div>
                    </div>
                  </button>
                  <div class="flex shrink-0 items-center gap-1">
                    <Button
                      variant="ghost"
                      icon="lucide-scroll-text"
                      :tooltip="
                        row.ai_transcript
                          ? __('Edit transcript')
                          : __('Save transcript')
                      "
                      @click="openTranscriptModal(row)"
                    />
                    <Button
                      variant="ghost"
                      icon="lucide-phone"
                      :disabled="!callEnabled || !dialNumber(row)"
                      :tooltip="__('Call')"
                      @click="quickCall(dialNumber(row))"
                    />
                  </div>
                </div>
                <div
                  v-if="recent.hasNextPage"
                  class="flex justify-center pt-3"
                >
                  <Button
                    variant="subtle"
                    :label="__('Load more')"
                    :loading="recent.loading"
                    @click="recent.next()"
                  />
                </div>
              </div>
            </div>

            <div v-else-if="listTab === 'hot'">
              <div
                v-if="hotLeads.loading && !hotLeads.data?.length"
                class="flex justify-center py-12"
              >
                <LoadingIndicator class="w-4" />
              </div>
              <div
                v-else-if="!hotLeads.data?.length"
                class="py-10 text-center text-p-sm text-ink-gray-5"
              >
                {{
                  __(
                    'No open leads with a phone number. Add a mobile number on a lead to call from here.',
                  )
                }}
              </div>
              <div v-else class="flex flex-col">
                <div
                  v-for="lead in hotLeads.data"
                  :key="lead.name"
                  class="flex w-full items-center justify-between gap-3 border-b border-outline-gray-modals py-3"
                >
                  <button
                    type="button"
                    class="flex min-w-0 flex-1 items-start gap-3 text-left transition hover:opacity-80"
                    @click="selectLead(lead)"
                  >
                    <Avatar
                      :label="lead.lead_name || lead.first_name || lead.name"
                      size="md"
                    />
                    <div class="min-w-0">
                      <div class="truncate text-p-base-medium text-ink-gray-8">
                        {{ lead.lead_name || lead.first_name || lead.name }}
                      </div>
                      <div class="mt-0.5 flex flex-wrap items-center gap-2">
                        <span
                          class="inline-flex items-center gap-1 text-p-sm text-ink-gray-6"
                        >
                          <IndicatorIcon
                            :class="getLeadStatus(lead.status)?.color"
                          />
                          {{ lead.status || __('—') }}
                        </span>
                        <span class="text-p-sm text-ink-gray-5">
                          {{ lead.mobile_no }}
                        </span>
                      </div>
                    </div>
                  </button>
                  <div class="flex shrink-0 items-center gap-1">
                    <Button
                      variant="ghost"
                      icon="lucide-panel-right-open"
                      :tooltip="__('Open lead')"
                      @click="openLeadPanel(lead)"
                    />
                    <Button
                      variant="ghost"
                      icon="lucide-phone"
                      :disabled="!callEnabled || !lead.mobile_no"
                      :tooltip="__('Call')"
                      @click="quickCall(lead.mobile_no)"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <aside
        class="flex w-full shrink-0 flex-col overflow-hidden bg-surface-gray-1 p-4 sm:p-6 lg:w-[360px] lg:min-w-[360px]"
      >
        <div class="min-h-0 w-full min-w-[280px] overflow-y-auto lg:min-w-[312px]">
          <div class="mb-4">
            <div class="text-lg-semibold text-ink-gray-8">
              {{ __('Phone') }}
            </div>
            <p class="mt-1 text-p-sm text-ink-gray-5">
              {{
                callEnabled
                  ? __('Dial using your assigned phone number.')
                  : __('Enable telephony in Settings to place calls.')
              }}
            </p>
          </div>

          <FormControl
            v-model="number"
            type="text"
            class="mb-4 [&_input]:text-center [&_input]:text-lg [&_input]:tracking-wide"
            :placeholder="__('Phone number')"
            autocomplete="tel"
          />

          <div class="mb-4 grid grid-cols-3 gap-2">
            <Button
              v-for="key in dialKeys"
              :key="key"
              size="lg"
              variant="subtle"
              class="h-12 text-base"
              :label="key"
              @click="appendDigit(key)"
            />
            <Button
              size="lg"
              variant="subtle"
              class="h-12"
              icon="lucide-delete"
              :tooltip="__('Backspace')"
              @click="backspace"
            />
            <Button
              size="lg"
              variant="subtle"
              class="h-12"
              label="0"
              @click="appendDigit('0')"
            />
            <Button
              size="lg"
              variant="subtle"
              class="h-12"
              label="+"
              @click="appendDigit('+')"
            />
          </div>

          <Button
            variant="solid"
            theme="green"
            size="lg"
            class="w-full"
            :label="__('Call')"
            icon-left="lucide-phone"
            :disabled="!canCall"
            @click="placeCall"
          />

          <div
            v-if="selectedLeadLabel"
            class="mt-4 rounded border border-outline-gray-modals bg-surface-white px-3 py-2 text-p-sm text-ink-gray-6"
          >
            {{ __('Calling') }}
            <span class="font-medium text-ink-gray-8">{{
              selectedLeadLabel
            }}</span>
          </div>
        </div>
      </aside>
      </div>

      <div
        class="h-full shrink-0 overflow-hidden border-l transition-[width,border-color] duration-300 ease-in-out motion-reduce:transition-none"
        :class="
          panelOpen
            ? 'border-outline-gray-modals'
            : 'border-transparent'
        "
        :style="{ width: panelOpen ? `${LEAD_PANEL_WIDTH}px` : '0px' }"
      >
        <div
          v-if="panelMounted"
          class="flex h-full flex-col justify-between"
          :style="{ width: `${LEAD_PANEL_WIDTH}px` }"
        >
          <div
            class="flex h-[45px] items-center gap-2 border-b px-3 py-2.5 text-lg-medium text-ink-gray-9"
          >
            <div
              class="min-w-0 flex-1 cursor-copy truncate px-2"
              @click="copyToClipboard(panelLeadId)"
            >
              {{ panelLeadId }}
            </div>
            <Button
              :tooltip="__('Open full page')"
              variant="ghost"
              icon="lucide-external-link"
              @click="
                router.push({ name: 'Lead', params: { leadId: panelLeadId } })
              "
            />
            <Button
              :tooltip="__('Close')"
              variant="ghost"
              icon="lucide-panel-right-close"
              @click="closeLeadPanel"
            />
          </div>
          <div
            v-if="leadSections.data"
            class="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            <SidePanelLayout
              :key="panelLeadId"
              :sections="leadSections.data"
              doctype="CRM Lead"
              :docname="panelLeadId"
              @reload="leadSections.reload()"
            />
          </div>
        </div>
      </div>
    </div>

    <SaveCallTranscriptModal
      v-model="showTranscriptModal"
      :call-log-name="transcriptCallLogName"
      @saved="recent.reload()"
    />
  </div>
</template>

<script setup>
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import SaveCallTranscriptModal from '@/components/Modals/SaveCallTranscriptModal.vue'
import SidePanelLayout from '@/components/SidePanelLayout.vue'
import { callEnabled } from '@/composables/telephony'
import { globalStore } from '@/stores/global'
import { statusesStore } from '@/stores/statuses'
import { copyToClipboard, formatDate } from '@/utils'
import {
  Avatar,
  Breadcrumbs,
  Button,
  FormControl,
  LoadingIndicator,
  TabButtons,
  createListResource,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import LucidePhoneIncoming from '~icons/lucide/phone-incoming'
import LucidePhoneOutgoing from '~icons/lucide/phone-outgoing'

const LEAD_PANEL_WIDTH = 352
const PANEL_ANIMATION_MS = 300

const router = useRouter()
const { makeCall } = globalStore()
const { getLeadStatus, leadStatuses } = statusesStore()

const number = ref('')
const selectedLeadLabel = ref('')
const panelLeadId = ref('')
const panelMounted = ref(false)
const panelOpen = ref(false)
const showTranscriptModal = ref(false)
const transcriptCallLogName = ref('')
const listTab = ref('recent')
const dialKeys = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
let panelCloseTimer = null

const leadSections = createResource({
  url: 'crm.fcrm.doctype.crm_fields_layout.crm_fields_layout.get_sidepanel_sections',
  cache: ['sidePanelSections', 'CRM Lead'],
  params: { doctype: 'CRM Lead' },
  auto: true,
})

const breadcrumbs = [{ label: __('Phone'), route: { name: 'Human Dialer' } }]

const listTabOptions = computed(() => [
  {
    label: __('Recent ({0})', [recent.data?.length || 0]),
    value: 'recent',
  },
  {
    label: __('Hot leads ({0})', [hotLeads.data?.length || 0]),
    value: 'hot',
  },
])

const canCall = computed(
  () => callEnabled.value && Boolean(number.value?.replace(/\s/g, '')),
)

const openLeadStatuses = computed(() => {
  const rows = leadStatuses.data || []
  return rows
    .filter((s) => s.type !== 'Lost' && s.type !== 'Converted')
    .map((s) => s.name)
})

const recent = createListResource({
  doctype: 'CRM Call Log',
  fields: [
    'name',
    'type',
    'status',
    'from',
    'to',
    'creation',
    'ai_transcript',
  ],
  orderBy: 'creation desc',
  pageLength: 20,
  auto: true,
})

const hotLeads = createListResource({
  doctype: 'CRM Lead',
  fields: [
    'name',
    'lead_name',
    'first_name',
    'mobile_no',
    'status',
    'modified',
  ],
  filters: {
    converted: 0,
    mobile_no: ['is', 'set'],
  },
  orderBy: 'modified desc',
  pageLength: 20,
  auto: false,
})

watch(
  openLeadStatuses,
  (statuses) => {
    if (statuses?.length) {
      hotLeads.filters = {
        converted: 0,
        mobile_no: ['is', 'set'],
        status: ['in', statuses],
      }
    } else {
      hotLeads.filters = {
        converted: 0,
        mobile_no: ['is', 'set'],
      }
    }
    hotLeads.reload()
  },
  { immediate: true },
)

function appendDigit(d) {
  number.value = `${number.value || ''}${d}`
}

function backspace() {
  number.value = (number.value || '').slice(0, -1)
}

function dialNumber(row) {
  if (row.type === 'Incoming') return row.from || ''
  return row.to || ''
}

function selectNumber(n) {
  if (!n) return
  number.value = n
  selectedLeadLabel.value = ''
}

function selectLead(lead) {
  number.value = lead.mobile_no || ''
  selectedLeadLabel.value = lead.lead_name || lead.first_name || lead.name
}

function openTranscriptModal(row) {
  transcriptCallLogName.value = row.name
  showTranscriptModal.value = true
}

function openLeadPanel(lead) {
  selectLead(lead)
  if (panelCloseTimer) {
    clearTimeout(panelCloseTimer)
    panelCloseTimer = null
  }
  panelLeadId.value = lead.name
  panelMounted.value = true
  nextTick(() => {
    panelOpen.value = true
  })
}

function closeLeadPanel() {
  panelOpen.value = false
  if (panelCloseTimer) clearTimeout(panelCloseTimer)
  panelCloseTimer = setTimeout(() => {
    panelMounted.value = false
    panelLeadId.value = ''
    panelCloseTimer = null
  }, PANEL_ANIMATION_MS)
}

onBeforeUnmount(() => {
  if (panelCloseTimer) clearTimeout(panelCloseTimer)
})

function quickCall(n) {
  const phone = (n || '').replace(/\s/g, '')
  if (!phone) return
  if (!callEnabled.value) {
    toast.error(__('Telephony is not enabled'))
    return
  }
  number.value = phone
  makeCall(phone)
}

function placeCall() {
  const n = (number.value || '').replace(/\s/g, '')
  if (!n) return
  if (!callEnabled.value) {
    toast.error(__('Telephony is not enabled'))
    return
  }
  makeCall(n)
}
</script>
