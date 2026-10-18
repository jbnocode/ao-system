<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex gap-1 items-center">
        <Button
          variant="ghost"
          icon-left="lucide-chevron-left"
          :label="__('Phone Numbers')"
          size="md"
          class="cursor-pointer -ml-4 hover:bg-transparent focus:bg-transparent focus:outline-none focus:ring-0 focus:ring-offset-0 focus-visible:none active:bg-transparent active:outline-none active:ring-0 active:ring-offset-0 active:text-ink-gray-5 text-2xl-semibold hover:opacity-70 !pr-0 !max-w-96 !justify-start"
          @click="emit('updateStep', 'telephony-settings')"
        />
      </div>
    </template>
    <template #description>
      <p class="text-p-base text-ink-gray-6">
        {{
          __(
            'Get numbers instantly for agents, or reassign numbers already on the account.',
          )
        }}
      </p>
    </template>
    <template #header-actions>
      <div class="flex gap-2">
        <Button
          :label="__('Refresh')"
          variant="subtle"
          icon-left="lucide-refresh-cw"
          :loading="numbers.loading || requests.loading"
          @click="reloadAll"
        />
        <Button
          v-if="twilioEnabled"
          :label="__('Get a number')"
          variant="solid"
          @click="openBuyDialog"
        />
      </div>
    </template>
    <template #content>
      <div
        v-if="pendingRequests.length"
        class="mb-6 rounded-5 border border-outline-gray-modals"
      >
        <div
          class="border-b border-outline-gray-modals px-3 py-2 text-p-sm-medium text-ink-gray-7"
        >
          {{ __('Requested numbers') }}
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
              · {{ __('Requested by {0}', [req.requested_by_name || req.requested_by]) }}
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

      <div v-if="!twilioEnabled" class="flex justify-center pt-[10%]">
        <div class="flex w-80 flex-col items-center gap-3 text-center">
          <PhoneIcon class="size-7.5 text-ink-gray-7" />
          <span class="text-lg-medium text-ink-gray-8">
            {{ __('Twilio is not enabled') }}
          </span>
          <span class="text-p-base text-ink-gray-6">
            {{
              isAdmin()
                ? __(
                    'Enable Twilio to fulfill queued requests and buy numbers.',
                  )
                : __(
                    'Submit a request from Telephony settings. A System Manager will connect Twilio, then anyone can fulfill pending requests instantly.',
                  )
            }}
          </span>
          <Button
            v-if="isAdmin()"
            :label="__('Twilio Settings')"
            variant="solid"
            @click="emit('updateStep', 'twilio-settings')"
          />
        </div>
      </div>

      <div v-else-if="numbers.loading && !numbers.data?.length" class="flex justify-center pt-[20%]">
        <LoadingIndicator class="size-6" />
      </div>

      <div v-else-if="!numbers.data?.length" class="flex justify-center pt-[15%]">
        <div class="flex w-72 flex-col items-center gap-3 text-center">
          <span class="text-lg-medium text-ink-gray-8">
            {{ __('No phone numbers yet') }}
          </span>
          <span class="text-p-base text-ink-gray-6">
            {{ __('Search Twilio and buy a number for an agent instantly.') }}
          </span>
          <Button
            :label="__('Get a number')"
            variant="solid"
            @click="openBuyDialog"
          />
        </div>
      </div>

      <div v-else class="flex flex-col">
        <div
          v-for="row in numbers.data"
          :key="row.sid || row.phone_number"
          class="flex items-center justify-between gap-4 border-b border-outline-gray-modals py-3"
        >
          <div class="min-w-0 flex flex-col gap-0.5">
            <div class="text-p-base-medium text-ink-gray-8 truncate">
              {{ row.phone_number }}
            </div>
            <div class="text-p-sm text-ink-gray-5 truncate">
              {{
                row.assigned_to
                  ? __('Assigned to {0}', [
                      row.assigned_to.user_name || row.assigned_to.user,
                    ])
                  : __('Unassigned')
              }}
              <span v-if="row.friendly_name && row.friendly_name !== row.phone_number">
                · {{ row.friendly_name }}
              </span>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Badge
              v-if="row.capabilities?.sms"
              :label="__('SMS')"
              variant="subtle"
              theme="gray"
            />
            <Button
              v-if="row.assigned_to"
              :label="__('Unassign')"
              variant="subtle"
              :loading="unassigning === row.phone_number"
              @click="unassign(row)"
            />
            <Button
              :label="row.assigned_to ? __('Reassign') : __('Assign')"
              variant="subtle"
              @click="openAssignDialog(row)"
            />
          </div>
        </div>
      </div>

      <ErrorMessage class="mt-4" :message="numbers.error" />
    </template>
  </SettingsLayoutBase>

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

  <Dialog v-model="showBuy" :options="{ title: __('Get a number') }">
    <template #body-content>
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <FormControl
            v-model="buyForm.country_code"
            :label="__('Country')"
            type="text"
            placeholder="US"
          />
          <FormControl
            v-model="buyForm.area_code"
            :label="__('Area code')"
            type="text"
            placeholder="415"
          />
        </div>
        <Button
          :label="__('Search')"
          variant="subtle"
          class="w-full"
          :loading="search.loading"
          @click="runSearch"
        />
        <ErrorMessage :message="search.error || buyError" />
        <div
          v-if="search.data?.length"
          class="max-h-64 overflow-y-auto divide-y divide-outline-gray-modals border border-outline-gray-modals rounded"
        >
          <button
            v-for="n in search.data"
            :key="n.phone_number"
            type="button"
            class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-surface-gray-1"
            :class="
              selectedBuy === n.phone_number ? 'bg-surface-gray-2' : ''
            "
            @click="selectedBuy = n.phone_number"
          >
            <div class="min-w-0">
              <div class="text-p-base-medium text-ink-gray-8">
                {{ n.phone_number }}
              </div>
              <div class="text-p-sm text-ink-gray-5 truncate">
                {{ [n.locality, n.region].filter(Boolean).join(', ') }}
              </div>
            </div>
            <Badge
              v-if="selectedBuy === n.phone_number"
              :label="__('Selected')"
              theme="green"
              variant="subtle"
            />
          </button>
        </div>
        <div v-else-if="search.data && !search.data.length" class="text-p-sm text-ink-gray-5">
          {{ __('No numbers found. Try another area code.') }}
        </div>
        <div>
          <label class="mb-1.5 block text-xs text-ink-gray-5">{{
            __('Assign to (optional)')
          }}</label>
          <Link
            :model-value="buyAssignUser"
            doctype="User"
            @update:model-value="buyAssignUser = $event"
          />
        </div>
      </div>
    </template>
    <template #actions>
      <Button
        variant="solid"
        class="w-full"
        :label="__('Buy number')"
        :loading="buying"
        :disabled="!selectedBuy"
        @click="purchase"
      />
    </template>
  </Dialog>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import { useTelephony } from '@/composables/telephony'
import { usersStore } from '@/stores/users'
import {
  Badge,
  Button,
  Dialog,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

const emit = defineEmits(['updateStep'])
const { isEnabled } = useTelephony()
const { isAdmin } = usersStore()
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
    (r) => r.status === 'Requested' || r.status === 'Pending' || r.status === 'Failed',
  ),
)

const fulfilling = ref('')

function reloadAll() {
  numbers.reload()
  requests.reload()
}

async function fulfillRequest(name) {
  fulfilling.value = name
  try {
    const data = await call('crm.integrations.twilio.api.fulfill_phone_number_request', {
      name,
    })
    toast.success(__('Number {0} assigned', [data?.phone_number || '']))
    reloadAll()
  } catch (err) {
    err?.messages?.forEach((msg) => toast.error(msg))
  } finally {
    fulfilling.value = ''
  }
}

const showAssign = ref(false)
const assignTarget = ref(null)
const assignUser = ref('')
const assigning = ref(false)
const assignError = ref('')
const unassigning = ref('')

const showBuy = ref(false)
const buyForm = reactive({ country_code: 'US', area_code: '' })
const selectedBuy = ref('')
const buyAssignUser = ref('')
const buying = ref(false)
const buyError = ref('')

const search = createResource({
  url: 'crm.integrations.twilio.api.search_available_numbers',
  onError: (err) => {
    err?.messages?.forEach((msg) => toast.error(msg))
  },
})

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
    numbers.reload()
  } catch (err) {
    assignError.value = err?.messages?.join('\n') || err?.message || __('Could not assign number')
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
    numbers.reload()
  } catch (err) {
    err?.messages?.forEach((msg) => toast.error(msg))
  } finally {
    unassigning.value = ''
  }
}

function openBuyDialog() {
  if (!twilioEnabled.value) {
    toast.error(__('Connect Twilio before buying numbers'))
    return
  }
  selectedBuy.value = ''
  buyAssignUser.value = ''
  buyError.value = ''
  search.data = null
  showBuy.value = true
}

function runSearch() {
  selectedBuy.value = ''
  search.submit({
    country_code: buyForm.country_code || 'US',
    area_code: buyForm.area_code || undefined,
    limit: 20,
  })
}

async function purchase() {
  if (!selectedBuy.value) return
  buying.value = true
  buyError.value = ''
  try {
    await call('crm.integrations.twilio.api.purchase_phone_number', {
      phone_number: selectedBuy.value,
      assign_to: buyAssignUser.value || undefined,
    })
    toast.success(__('Number purchased'))
    showBuy.value = false
    reloadAll()
  } catch (err) {
    buyError.value =
      err?.messages?.join('\n') || err?.message || __('Could not purchase number')
  } finally {
    buying.value = false
  }
}
</script>
