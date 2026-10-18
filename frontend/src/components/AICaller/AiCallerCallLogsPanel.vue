<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
    <div
      class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-outline-gray-modals px-4 py-3"
    >
      <div>
        <div class="text-p-base-medium text-ink-gray-8">
          {{ __('Call logs') }}
        </div>
        <p class="mt-0.5 text-p-sm text-ink-gray-5">
          {{
            isManager
              ? __('All team calls from AI and phone.')
              : __('Your calls from AI and phone.')
          }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <CustomActions
          v-if="callLogsListView?.customListActions"
          :actions="callLogsListView.customListActions"
        />
        <Button
          variant="solid"
          :label="__('Create')"
          icon-left="lucide-plus"
          @click="createCallLog"
        />
      </div>
    </div>

    <ViewControls
      ref="viewControls"
      v-model="callLogs"
      v-model:loadMore="loadMore"
      v-model:resizeColumn="triggerResize"
      v-model:updatedPageCount="updatedPageCount"
      doctype="CRM Call Log"
    />

    <div class="min-h-0 flex-1 overflow-auto">
      <CallLogsListView
        v-if="callLogs.data && rows.length"
        ref="callLogsListView"
        v-model="callLogs.data.page_length_count"
        v-model:list="callLogs"
        :rows="rows"
        :columns="columns"
        :options="{
          showTooltip: false,
          resizeColumn: true,
          rowCount: callLogs.data.row_count,
          totalCount: callLogs.data.total_count,
        }"
        @showCallLog="showCallLog"
        @loadMore="() => loadMore++"
        @columnWidthUpdated="() => triggerResize++"
        @updatePageCount="(count) => (updatedPageCount = count)"
        @applyFilter="(data) => viewControls.applyFilter(data)"
        @applyLikeFilter="(data) => viewControls.applyLikeFilter(data)"
        @likeDoc="(data) => viewControls.likeDoc(data)"
        @selectionsChanged="
          (selections) => viewControls.updateSelections(selections)
        "
      />
      <EmptyState
        v-else-if="callLogs.data && !rows.length"
        name="Call Logs"
        :icon="PhoneIcon"
        :title="__('No call logs yet')"
        :description="
          __(
            'AI and phone calls are logged here, along with calls you log by hand.',
          )
        "
        :filtered="!!Object.keys(callLogs.params?.filters || {}).length"
        @create="createCallLog()"
      />
    </div>

    <CallLogDetailModal
      v-model="showCallLogDetailModal"
      v-model:callLog="callLog"
    />
  </div>
</template>

<script setup>
import CustomActions from '@/components/CustomActions.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import CallLogsListView from '@/components/ListViews/CallLogsListView.vue'
import EmptyState from '@/components/ListViews/EmptyState.vue'
import CallLogDetailModal from '@/components/Modals/CallLogDetailModal.vue'
import ViewControls from '@/components/ViewControls.vue'
import { useDoctypeModal } from '@/composables/doctypeModal'
import { getCallLogDetail } from '@/utils/callLog'
import { useTelemetry } from '@framework/ui/telemetry'
import { Button, createResource } from 'frappe-ui'
import { computed, ref } from 'vue'

defineProps({
  isManager: { type: Boolean, default: false },
})

const callLogsListView = ref(null)
const callLogs = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (
    !callLogs.value?.data?.data ||
    !['list', 'group_by'].includes(callLogs.value.data.view_type)
  )
    return []
  return callLogs.value?.data.data.map((row) => {
    let _rows = {}
    callLogs.value?.data.rows.forEach((key) => {
      _rows[key] = getCallLogDetail(key, row, callLogs.value?.data.columns)
    })
    return _rows
  })
})

const columns = computed(() => {
  let _columns = callLogs.value?.data?.columns || []
  if (_columns.length) {
    _columns = _columns.map((col, index) => {
      if (index === _columns.length - 1) {
        return { ...col, align: 'right' }
      }
      return col
    })
  }
  return _columns
})

const showCallLogDetailModal = ref(false)
const callLog = ref({})

function showCallLog(name) {
  showCallLogDetailModal.value = true
  callLog.value = createResource({
    url: 'crm.fcrm.doctype.crm_call_log.crm_call_log.get_call_log',
    params: { name },
    cache: ['call_log', name],
    auto: true,
  })
}

const { showModal } = useDoctypeModal()
const { capture } = useTelemetry()

function createCallLog() {
  showModal({
    doctype: 'CRM Call Log',
    title: 'Call Log',
    callbacks: {
      afterInsert: () => {
        capture('call_log_created')
        callLogs.value.reload()
      },
    },
  })
}
</script>
