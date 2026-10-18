<template>
  <div>
    <div class="mb-3 flex items-center justify-between gap-2">
      <div class="text-p-base-medium text-ink-gray-8">
        {{ __('Numbers') }}
      </div>
      <Button
        variant="subtle"
        size="sm"
        icon-left="lucide-refresh-cw"
        :label="__('Refresh')"
        :loading="numbers.loading || requests.loading"
        @click="reloadAll"
      />
    </div>

    <div
      v-if="pendingRequests.length"
      class="mb-4 rounded-5 border border-outline-gray-modals"
    >
      <div
        class="border-b border-outline-gray-modals px-3 py-2 text-p-sm-medium text-ink-gray-7"
      >
        {{ __('Requested') }}
      </div>
      <div
        v-for="req in pendingRequests"
        :key="req.name"
        class="flex flex-col gap-2 border-b border-outline-gray-modals px-3 py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="min-w-0 text-p-sm text-ink-gray-6">
          <div class="text-p-base-medium text-ink-gray-8">
            {{ req.assign_to_name || req.assign_to }}
          </div>
          <div>
            {{ req.country_code
            }}{{ req.area_code ? ` · ${req.area_code}` : '' }}
            ·
            {{
              __('Requested by {0}', [
                req.requested_by_name || req.requested_by,
              ])
            }}
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <Badge :label="__('Requested')" theme="amber" variant="subtle" />
          <Button
            v-if="twilioEnabled"
            size="sm"
            variant="solid"
            :label="__('Fulfill now')"
            :loading="fulfilling === req.name"
            @click="fulfillRequest(req.name)"
          />
        </div>
      </div>
    </div>

    <div
      v-if="numbers.loading && !numbers.data?.length"
      class="flex justify-center py-8"
    >
      <LoadingIndicator class="size-5" />
    </div>
    <div
      v-else-if="!numbers.data?.length"
      class="rounded-5 border border-dashed border-outline-gray-modals px-4 py-8 text-center text-p-sm text-ink-gray-5"
    >
      {{ __('No numbers on the account yet. Request one above.') }}
    </div>
    <div v-else class="flex flex-col rounded-5 border border-outline-gray-modals">
      <div
        v-for="row in numbers.data"
        :key="row.sid || row.phone_number"
        class="flex items-center justify-between gap-4 border-b border-outline-gray-modals px-3 py-3 last:border-b-0"
      >
        <div class="min-w-0 flex flex-col gap-0.5">
          <div class="truncate text-p-base-medium text-ink-gray-8">
            {{ row.phone_number }}
          </div>
          <div class="truncate text-p-sm text-ink-gray-5">
            {{
              row.assigned_to
                ? __('Assigned to {0}', [
                    row.assigned_to.user_name || row.assigned_to.user,
                  ])
                : __('Unassigned')
            }}
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <Button
            v-if="row.assigned_to"
            size="sm"
            :label="__('Unassign')"
            variant="subtle"
            :loading="unassigning === row.phone_number"
            @click="unassign(row)"
          />
          <Button
            size="sm"
            :label="row.assigned_to ? __('Reassign') : __('Assign')"
            variant="subtle"
            @click="openAssignDialog(row)"
          />
        </div>
      </div>
    </div>

    <ErrorMessage class="mt-3" :message="numbers.error" />

    <Dialog v-model="showAssign" :options="{ title: __('Assign number') }">
      <template #body-content>
        <div class="space-y-4">
          <div class="text-p-sm text-ink-gray-6">
            {{ assignTarget?.phone_number }}
          </div>
          <div>
            <label class="mb-1.5 block text-xs text-ink-gray-5">{{
              __('Agent')
            }}</label>
            <Link
              :model-value="assignUser"
              doctype="User"
              @update:model-value="assignUser = $event"
            />
          </div>
          <ErrorMessage :message="assignError" />
        </div>
      </template>
      <template #actions>
        <Button
          variant="solid"
          class="w-full"
          :label="__('Assign')"
          :loading="assigning"
          :disabled="!assignUser"
          @click="assign"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import { useTelephony } from '@/composables/telephony'
import {
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  LoadingIndicator,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, ref } from 'vue'

const { isEnabled } = useTelephony()
const twilioEnabled = computed(() => isEnabled('twilio'))

const numbers = createResource({
  url: 'crm.integrations.twilio.api.list_phone_numbers',
  auto: true,
  onError: (err) => {
    err?.messages?.forEach((msg) => toast.error(msg))
  },
})

const requests = createResource({
  url: 'crm.integrations.twilio.api.list_phone_number_requests',
  auto: true,
  makeParams: () => ({}),
})

const pendingRequests = computed(() =>
  (requests.data || []).filter(
    (r) =>
      r.status === 'Requested' ||
      r.status === 'Pending' ||
      r.status === 'Failed',
  ),
)

const fulfilling = ref('')
const showAssign = ref(false)
const assignTarget = ref(null)
const assignUser = ref('')
const assigning = ref(false)
const assignError = ref('')
const unassigning = ref('')

function reloadAll() {
  numbers.reload()
  requests.reload()
}

defineExpose({ reloadAll })

async function fulfillRequest(name) {
  fulfilling.value = name
  try {
    const data = await call(
      'crm.integrations.twilio.api.fulfill_phone_number_request',
      { name },
    )
    toast.success(__('Number {0} assigned', [data?.phone_number || '']))
    reloadAll()
  } catch (err) {
    err?.messages?.forEach((msg) => toast.error(msg))
  } finally {
    fulfilling.value = ''
  }
}

function openAssignDialog(row) {
  assignTarget.value = row
  assignUser.value = row.assigned_to?.user || ''
  assignError.value = ''
  showAssign.value = true
}

async function assign() {
  if (!assignTarget.value?.phone_number || !assignUser.value) return
  assigning.value = true
  assignError.value = ''
  try {
    await call('crm.integrations.twilio.api.assign_phone_number', {
      phone_number: assignTarget.value.phone_number,
      user: assignUser.value,
    })
    toast.success(__('Number assigned'))
    showAssign.value = false
    reloadAll()
  } catch (err) {
    assignError.value =
      err?.messages?.join('\n') || err?.message || __('Could not assign number')
  } finally {
    assigning.value = false
  }
}

async function unassign(row) {
  unassigning.value = row.phone_number
  try {
    await call('crm.integrations.twilio.api.unassign_phone_number', {
      phone_number: row.phone_number,
      user: row.assigned_to?.user,
    })
    toast.success(__('Number unassigned'))
    reloadAll()
  } catch (err) {
    err?.messages?.forEach((msg) => toast.error(msg))
  } finally {
    unassigning.value = ''
  }
}
</script>
