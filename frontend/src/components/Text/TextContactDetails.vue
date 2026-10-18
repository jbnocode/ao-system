<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-base">
    <div
      class="flex h-[45px] shrink-0 items-center gap-2 border-b border-outline-gray-modals px-3 py-2.5 text-lg-medium text-ink-gray-9"
    >
      <div
        class="min-w-0 flex-1 cursor-copy truncate px-2"
        @click="copyHeader"
      >
        {{ headerLabel }}
      </div>
      <Button
        v-if="showClose"
        :tooltip="__('Close')"
        variant="ghost"
        icon="lucide-x"
        @click="$emit('close')"
      />
      <Button
        v-else-if="collapse"
        :tooltip="__('Collapse')"
        variant="ghost"
        icon="lucide-panel-right-close"
        @click="collapse()"
      />
    </div>

    <div
      v-if="party.loading && !party.data"
      class="flex flex-1 items-center justify-center py-10"
    >
      <LoadingIndicator class="w-4" />
    </div>

    <div v-else class="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <div
        class="flex flex-col items-center gap-3 border-b border-outline-gray-modals px-5 py-6 text-center"
      >
        <Avatar
          size="3xl"
          class="size-16"
          :label="displayName"
          :image="party.data?.image"
        />
        <div class="min-w-0 w-full">
          <div class="truncate text-xl-medium text-ink-gray-9">
            {{ displayName }}
          </div>
          <div class="mt-0.5 truncate text-p-sm text-ink-gray-5">
            {{ party.data?.email || phone || __('—') }}
          </div>
          <Badge
            class="mt-2"
            variant="subtle"
            :theme="isLinked ? 'blue' : 'gray'"
            :label="isLinked ? linkBadgeLabel : __('Not linked')"
          />
        </div>
        <div class="flex items-center justify-center gap-1.5">
          <Button
            v-if="callEnabled"
            :tooltip="__('Make a Call')"
            :icon="PhoneIcon"
            @click="onCall"
          />
          <Button
            :tooltip="__('Send an Email')"
            :icon="Email2Icon"
            @click="onEmail"
          />
          <Button
            v-if="recordRoute"
            :tooltip="__('Open record')"
            :icon="LinkIcon"
            @click="openRecord"
          />
        </div>
      </div>

      <div class="px-4 pt-4">
        <div
          class="flex flex-col gap-2.5 rounded-6 bg-surface-gray-1 px-3 py-3 text-p-sm"
        >
          <div
            v-for="row in infoRows"
            :key="row.label"
            class="flex items-start gap-2"
          >
            <component
              :is="row.icon"
              class="mt-0.5 size-3.5 shrink-0 text-ink-gray-5"
            />
            <div class="min-w-0 flex-1">
              <div class="text-ink-gray-5">{{ row.label }}</div>
              <div
                class="truncate"
                :class="
                  row.value ? 'text-ink-gray-8' : 'text-ink-gray-4 italic'
                "
              >
                {{ row.value || __('—') }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="mt-4 flex min-h-0 flex-1 flex-col px-4 pb-4">
        <Tabs v-model="activeTab" :tabs="tabs" as="div">
          <template #tab-panel="{ tab }">
            <div
              v-if="tab.name === 'details'"
              class="flex flex-col gap-3 pt-3"
            >
              <div
                v-for="field in detailFields"
                :key="field.label"
                class="flex gap-2 text-p-sm"
              >
                <div class="w-[40%] shrink-0 text-ink-gray-5">
                  {{ field.label }}
                </div>
                <div
                  class="min-w-0 flex-1 truncate"
                  :class="
                    field.value ? 'text-ink-gray-8' : 'text-ink-gray-4 italic'
                  "
                >
                  {{ field.value || __('—') }}
                </div>
              </div>
              <Button
                v-if="recordRoute"
                class="mt-2 self-start"
                variant="solid"
                :label="__('View record')"
                @click="openRecord"
              />
            </div>
            <div
              v-else-if="tab.name === 'messages'"
              class="flex flex-col gap-2 pt-3 text-p-sm text-ink-gray-6"
            >
              <div>
                {{ __('{0} messages in this thread', [messageCount]) }}
              </div>
              <div
                v-if="lastPreview"
                class="rounded-4 bg-surface-gray-1 px-3 py-2 text-ink-gray-8"
              >
                {{ lastPreview }}
              </div>
              <div v-else class="italic text-ink-gray-4">
                {{ __('—') }}
              </div>
            </div>
          </template>
        </Tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import Email2Icon from '@/components/Icons/Email2Icon.vue'
import LinkIcon from '@/components/Icons/LinkIcon.vue'
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import { callEnabled } from '@/composables/telephony'
import { globalStore } from '@/stores/global'
import { copyToClipboard } from '@/utils'
import {
  Avatar,
  Badge,
  Button,
  LoadingIndicator,
  Tabs,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import LucideBriefcase from '~icons/lucide/briefcase'
import LucideMail from '~icons/lucide/mail'
import LucidePhone from '~icons/lucide/phone'
import LucideUser from '~icons/lucide/user'

const props = defineProps({
  phone: { type: String, default: '' },
  title: { type: String, default: '' },
  messageCount: { type: Number, default: 0 },
  lastPreview: { type: String, default: '' },
  showClose: { type: Boolean, default: false },
  collapse: { type: Function, default: null },
})

const emit = defineEmits(['close'])

const router = useRouter()
const { makeCall } = globalStore()
const activeTab = ref(0)

const tabs = [
  { label: __('Details'), name: 'details' },
  { label: __('Messages'), name: 'messages' },
]

const party = createResource({
  url: 'crm.api.sms.get_party',
  makeParams() {
    return { phone: props.phone }
  },
})

watch(
  () => props.phone,
  (phone) => {
    if (phone) party.reload()
  },
  { immediate: true },
)

const isLinked = computed(
  () => Boolean(party.data?.reference_doctype && party.data?.reference_name),
)

const displayName = computed(() => {
  const title = party.data?.title
  if (title && title !== party.data?.phone && title !== props.phone) {
    return title
  }
  return props.title || props.phone || __('Unknown')
})

const headerLabel = computed(() => {
  if (isLinked.value) return party.data.reference_name
  return props.phone || displayName.value
})

const linkBadgeLabel = computed(() => {
  const dt = party.data?.reference_doctype
  if (dt === 'CRM Lead') return __('Lead')
  if (dt === 'CRM Deal') return __('Deal')
  if (dt === 'Contact') return __('Contact')
  return dt || __('Linked')
})

const recordRoute = computed(() => {
  const dt = party.data?.reference_doctype
  const name = party.data?.reference_name
  if (!dt || !name) return null
  if (dt === 'CRM Lead') return { name: 'Lead', params: { leadId: name } }
  if (dt === 'CRM Deal') return { name: 'Deal', params: { dealId: name } }
  if (dt === 'Contact') return { name: 'Contact', params: { contactId: name } }
  return null
})

const infoRows = computed(() => {
  const p = party.data || {}
  return [
    {
      label: __('Phone'),
      value: p.mobile_no || props.phone || '',
      icon: LucidePhone,
    },
    { label: __('Email'), value: p.email || '', icon: LucideMail },
    {
      label: __('Organization'),
      value: p.organization || '',
      icon: LucideBriefcase,
    },
    { label: __('Job title'), value: p.job_title || '', icon: LucideUser },
  ]
})

const detailFields = computed(() => {
  const p = party.data || {}
  return [
    { label: __('Status'), value: p.status || '' },
    { label: __('Owner'), value: p.owner_name || p.owner || '' },
    {
      label: __('Linked'),
      value: isLinked.value
        ? `${p.reference_doctype}: ${p.reference_name}`
        : '',
    },
    { label: __('Website'), value: p.website || '' },
  ]
})

function copyHeader() {
  copyToClipboard(headerLabel.value)
}

function onCall() {
  const number = party.data?.mobile_no || props.phone
  if (!number) {
    toast.error(__('Please set a mobile number to make calls'))
    return
  }
  makeCall(number)
}

function onEmail() {
  const email = party.data?.email
  if (!email) {
    toast.error(__('Please set an email address to send emails'))
    return
  }
  window.location.href = `mailto:${email}`
}

function openRecord() {
  if (recordRoute.value) {
    emit('close')
    router.push(recordRoute.value)
  }
}
</script>
