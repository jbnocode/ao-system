<template>
  <div class="flex h-full flex-col gap-6 px-6 py-8">
    <div class="flex justify-between px-2 text-ink-gray-8">
      <div class="flex w-9/12 flex-col gap-1">
        <h2
          class="flex h-5 gap-2 text-2xl-semibold leading-none text-ink-gray-8"
        >
          {{ __('Telephony Settings') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            isManager()
              ? __('Request and assign phone numbers for your agents.')
              : __('Configure your personal calling preferences.')
          }}
        </p>
      </div>
      <div
        v-if="!isManager() && isDirty"
        class="flex w-3/12 item-center justify-end space-x-2"
      >
        <Button
          :loading="
            isNewDoc ? insertResource.loading : telephonyAgent.save?.loading
          "
          :label="__('Update')"
          variant="solid"
          @click="update"
        />
      </div>
    </div>

    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <!-- System Manager: connect Twilio / Exotel -->
      <div v-if="isAdmin()" class="mb-6 space-y-1 px-2">
        <div class="flex items-center justify-between py-3">
          <div class="flex flex-col gap-1">
            <span class="text-base-medium text-ink-gray-8">{{
              __('Twilio')
            }}</span>
            <span class="text-p-sm text-ink-gray-6">
              {{
                __(
                  'Connect the platform Twilio account (SID, auth token). System Manager only.',
                )
              }}
            </span>
          </div>
          <Button
            :label="
              isEnabled('twilio')
                ? __('Update Configuration')
                : __('Configure')
            "
            @click="emit('updateStep', 'twilio-settings')"
          />
        </div>
        <div class="h-px border-t border-outline-elevation-2" />
        <div class="flex items-center justify-between py-3">
          <div class="flex flex-col gap-1">
            <span class="text-base-medium text-ink-gray-8">{{
              __('Exotel')
            }}</span>
            <span class="text-p-sm text-ink-gray-6">
              {{ __('Connect Exotel for the platform. System Manager only.') }}
            </span>
          </div>
          <Button
            :label="
              isEnabled('exotel')
                ? __('Update Configuration')
                : __('Configure')
            "
            @click="emit('updateStep', 'exotel-settings')"
          />
        </div>
      </div>

      <!-- Manager: request + inventory -->
      <template v-if="isManager()">
        <div
          class="rounded-5 border border-outline-gray-modals bg-surface-gray-1 p-4"
        >
          <div class="mb-1 text-p-base-medium text-ink-gray-8">
            {{ __('Request a number') }}
          </div>
          <p class="mb-3 text-p-sm text-ink-gray-5">
            {{
              __(
                'Requests a number for an agent. When Twilio is available it is bought and assigned automatically; otherwise it stays Requested until fulfilled.',
              )
            }}
          </p>
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
            <FormControl
              v-model="acquireForm.country_code"
              class="sm:w-24"
              :label="__('Country')"
              type="text"
              placeholder="US"
            />
            <FormControl
              v-model="acquireForm.area_code"
              class="sm:w-28"
              :label="__('Area code')"
              type="text"
              placeholder="415"
            />
            <div class="min-w-0 flex-1">
              <label class="mb-1.5 block text-xs text-ink-gray-5">{{
                __('Assign to')
              }}</label>
              <Link
                :model-value="acquireForm.assign_to"
                doctype="User"
                @update:model-value="acquireForm.assign_to = $event"
              />
            </div>
            <Button
              variant="solid"
              :label="__('Request number')"
              :loading="acquiring"
              :disabled="!acquireForm.assign_to"
              @click="submitAcquire"
            />
          </div>
          <ErrorMessage
            v-if="acquireError"
            class="mt-2"
            :message="acquireError"
          />
          <p v-if="acquireSuccess" class="mt-2 text-p-sm text-ink-gray-6">
            {{ acquireSuccess }}
          </p>
        </div>

        <div class="mt-6 px-1">
          <PhoneNumberInventory ref="inventoryRef" />
        </div>
      </template>

      <!-- Agent (non-manager): personal calling prefs -->
      <div v-else-if="telephonyAgent.doc" class="flex flex-col">
        <div class="flex items-center justify-between gap-8 py-3 pl-2 pr-1">
          <div class="flex flex-col">
            <div class="truncate text-p-base-medium text-ink-gray-7">
              {{ __('Default Medium') }}
            </div>
            <div class="text-p-sm text-ink-gray-5">
              {{ __('Default calling medium for logged-in user') }}
            </div>
          </div>
          <div class="flex items-center gap-1">
            <FormControl
              v-model="telephonyAgent.doc.default_medium"
              type="select"
              class="w-44 p-1"
              :options="[
                { label: __(''), value: '' },
                { label: __('Twilio'), value: 'Twilio' },
                { label: __('Exotel'), value: 'Exotel' },
              ]"
              :placeholder="__('Select Medium')"
            />
            <Button
              v-if="telephonyAgent.doc.default_medium"
              icon="lucide-x"
              :tooltip="__('Clear')"
              @click="telephonyAgent.doc.default_medium = ''"
            />
          </div>
        </div>
        <div
          v-if="isEnabled('twilio')"
          class="mx-2 h-px border-t border-outline-elevation-2"
        />
        <div
          v-if="isEnabled('twilio')"
          class="flex items-center justify-between gap-8 py-3 pl-2 pr-1"
        >
          <div class="flex flex-col">
            <div class="truncate text-p-base-medium text-ink-gray-7">
              {{ __('Twilio Number') }}
            </div>
            <div class="text-p-sm text-ink-gray-5">
              {{ __('Set the Twilio number to be used for outgoing calls.') }}
            </div>
          </div>
          <FormControl
            v-model="telephonyAgent.doc.twilio_number"
            class="w-44 flex-1 truncate p-1"
            :placeholder="__('Enter Twilio Number')"
            :error="
              Boolean(telephonyAgent.doc.twilio_number) &&
              !validatePhone(telephonyAgent.doc.twilio_number)
                ? __('Enter a valid phone number')
                : undefined
            "
            placement="bottom-end"
          />
        </div>
        <div
          v-if="isEnabled('exotel')"
          class="mx-2 h-px border-t border-outline-elevation-2"
        />
        <div
          v-if="isEnabled('exotel')"
          class="flex items-center justify-between gap-8 py-3 pl-2 pr-1"
        >
          <div class="flex flex-col">
            <div class="truncate text-p-base-medium text-ink-gray-7">
              {{ __('Exotel Number') }}
            </div>
            <div class="text-p-sm text-ink-gray-5">
              {{ __('Set the Exotel number to be used for outgoing calls.') }}
            </div>
          </div>
          <FormControl
            v-model="telephonyAgent.doc.exotel_number"
            class="w-44 flex-1 truncate p-1"
            :placeholder="__('Enter Exotel Number')"
            :error="
              Boolean(telephonyAgent.doc.exotel_number) &&
              !validatePhone(telephonyAgent.doc.exotel_number)
                ? __('Enter a valid phone number')
                : undefined
            "
            placement="bottom-end"
          />
        </div>
      </div>
    </div>
    <ErrorMessage
      v-if="!isManager()"
      :message="isNewDoc ? insertResource.error : telephonyAgent.save?.error"
    />
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import PhoneNumberInventory from '@/components/Settings/Telephony/PhoneNumberInventory.vue'
import { useTelephony } from '@/composables/telephony'
import { useDocument } from '@/data/document'
import { usersStore } from '@/stores/users'
import { validatePhone } from '@/utils'
import {
  Button,
  ErrorMessage,
  FormControl,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'

const { isEnabled } = useTelephony()
const emit = defineEmits(['updateStep'])
const { getUser, isManager, isAdmin } = usersStore()

const inventoryRef = ref(null)

const acquireForm = reactive({
  country_code: 'US',
  area_code: '',
  assign_to: getUser().name || '',
})
const acquiring = ref(false)
const acquireError = ref('')
const acquireSuccess = ref('')

async function submitAcquire() {
  if (!acquireForm.assign_to) return
  acquiring.value = true
  acquireError.value = ''
  acquireSuccess.value = ''
  try {
    const data = await call(
      'crm.integrations.twilio.api.request_or_acquire_phone_number',
      {
        country_code: acquireForm.country_code || 'US',
        area_code: acquireForm.area_code || undefined,
        assign_to: acquireForm.assign_to,
      },
    )
    if (data?.status === 'Fulfilled') {
      acquireSuccess.value =
        data?.message ||
        __('Number {0} assigned to agent.', [data.phone_number])
      toast.success(__('Number assigned'))
    } else {
      acquireSuccess.value = data?.message || __('Number requested.')
      toast.success(__('Number requested'))
    }
    inventoryRef.value?.reloadAll?.()
  } catch (err) {
    acquireError.value =
      err?.messages?.join('\n') ||
      err?.message ||
      __('Could not complete request')
  } finally {
    acquiring.value = false
  }
}

const isNewDoc = ref(false)

const { document: telephonyAgent } = useDocument(
  'CRM Telephony Agent',
  getUser().name,
  {
    onError: (err) => {
      if (err.exc_type === 'DoesNotExistError') {
        isNewDoc.value = true
        telephonyAgent.doc = {}
        telephonyAgent.originalDoc = {}
      }
    },
  },
)

const insertResource = createResource({
  url: 'frappe.client.insert',
  onSuccess: (data) => {
    isNewDoc.value = false
    telephonyAgent.doc = data
    telephonyAgent.originalDoc = JSON.parse(JSON.stringify(data))
    toast.success(__('Document created successfully'))
  },
  onError: (err) => {
    err.messages?.forEach((msg) => toast.error(msg))
  },
})

function update() {
  if (!isDirty.value) return
  if (isNewDoc.value) {
    insertResource.submit({
      doc: {
        doctype: 'CRM Telephony Agent',
        user: getUser().name,
        ...telephonyAgent.doc,
      },
    })
  } else {
    telephonyAgent.save.submit()
  }
}

const isDirty = computed(() => {
  return (
    telephonyAgent.doc &&
    telephonyAgent.originalDoc &&
    JSON.stringify(telephonyAgent.doc) !==
      JSON.stringify(telephonyAgent.originalDoc)
  )
})
</script>
