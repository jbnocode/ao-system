<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
    </LayoutHeader>

    <div
      class="flex min-h-0 flex-1 overflow-hidden bg-surface-white"
    >
      <!-- Left: conversations -->
      <div
        class="flex min-h-0 w-full flex-col border-r border-outline-gray-modals lg:w-80 lg:shrink-0"
        :class="selectedPhone ? 'hidden lg:flex' : 'flex'"
      >
        <div
          class="flex flex-col gap-2 border-b border-outline-gray-modals px-3 py-3"
        >
          <div class="relative">
            <TextInput
              v-model="search"
              type="text"
              size="sm"
              :placeholder="__('Search conversations')"
              :debounce="200"
            >
              <template #prefix>
                <LucideSearch class="size-4 text-ink-gray-5" />
              </template>
            </TextInput>
            <Button
              v-if="search"
              icon="lucide-x"
              variant="ghost"
              class="absolute right-0.5 top-1/2 -translate-y-1/2"
              @click="search = ''"
            />
          </div>
          <div class="flex items-center gap-1.5">
            <FormControl
              v-model="typeFilter"
              type="select"
              size="sm"
              class="min-w-0 flex-1"
              :options="typeFilterOptions"
            />
            <FormControl
              v-model="linkFilter"
              type="select"
              size="sm"
              class="min-w-0 flex-1"
              :options="linkFilterOptions"
            />
          </div>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-2 pb-4 pt-1">
          <div
            v-if="conversations.loading && !conversations.data?.length"
            class="flex justify-center py-12"
          >
            <LoadingIndicator class="w-4" />
          </div>
          <div
            v-else-if="!conversations.data?.length"
            class="px-2 py-10 text-center text-p-sm text-ink-gray-5"
          >
            {{ __('No texts yet. Seed demo data or wait for an inbound SMS.') }}
          </div>
          <div
            v-else-if="!filteredConversations.length"
            class="px-2 py-10 text-center text-p-sm text-ink-gray-5"
          >
            {{ __('No conversations match your filters.') }}
          </div>
          <button
            v-for="row in filteredConversations"
            :key="row.phone"
            type="button"
            class="flex w-full items-start gap-3 rounded-4 px-2 py-2.5 text-left transition hover:bg-surface-gray-1"
            :class="
              selectedPhone === row.phone
                ? 'bg-surface-white shadow-sm ring-1 ring-outline-gray-modals'
                : undefined
            "
            @click="selectConversation(row.phone)"
          >
            <Avatar
              size="lg"
              class="mt-0.5 shrink-0"
              :label="row.title || row.phone"
            />
            <div class="min-w-0 flex-1">
              <div class="flex items-baseline justify-between gap-2">
                <div class="truncate text-p-base-medium text-ink-gray-8">
                  {{ row.title || row.phone }}
                </div>
                <div class="shrink-0 text-2xs text-ink-gray-5">
                  {{ formatDate(row.creation, 'MMM D') }}
                </div>
              </div>
              <div class="truncate text-p-sm text-ink-gray-5">
                <span v-if="row.type === 'Outgoing'">{{ __('You') }}: </span>
                {{ row.preview }}
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Center: thread -->
      <div
        class="flex min-h-0 min-w-0 flex-1 flex-col"
        :class="!selectedPhone ? 'hidden lg:flex' : 'flex'"
      >
        <template v-if="selectedPhone">
          <div
            class="flex items-center gap-2 border-b border-outline-gray-modals px-4 py-2.5"
          >
            <Button
              class="lg:hidden"
              variant="ghost"
              icon="lucide-arrow-left"
              @click="selectedPhone = ''"
            />
            <Avatar
              size="md"
              class="shrink-0"
              :label="selectedTitle"
            />
            <div class="min-w-0 flex-1">
              <div class="truncate text-p-base-medium text-ink-gray-8">
                {{ selectedTitle }}
              </div>
              <div class="truncate text-p-sm text-ink-gray-5">
                {{ selectedPhone }}
              </div>
            </div>
            <Button
              class="lg:hidden"
              variant="ghost"
              :tooltip="__('Contact details')"
              icon="lucide-panel-right-open"
              @click="showContactSheet = true"
            />
          </div>
          <FadedScrollableDiv
            ref="threadScroll"
            class="flex min-h-0 flex-1 flex-col overflow-y-auto px-3 py-4 sm:px-6"
          >
            <div
              v-if="messages.loading && !messages.data?.length"
              class="flex justify-center py-12"
            >
              <LoadingIndicator class="w-4" />
            </div>
            <div
              v-else-if="!messages.data?.length"
              class="py-10 text-center text-p-sm text-ink-gray-5"
            >
              {{ __('No messages in this thread yet.') }}
            </div>
            <TextArea v-else :messages="messages.data" />
          </FadedScrollableDiv>
          <div class="border-t border-outline-gray-modals">
            <TextBox
              :phone="selectedPhone"
              :disabled="!smsEnabled"
              @sent="onSent"
            />
          </div>
        </template>
        <div
          v-else
          class="hidden flex-1 items-center justify-center text-p-sm text-ink-gray-5 lg:flex"
        >
          {{ __('Select a conversation') }}
        </div>
      </div>

      <!-- Right: contact panel (desktop). Wrapper owns visibility because
           Resizer puts class attrs on its inner absolute layer. -->
      <div
        v-if="selectedPhone"
        class="flex h-full shrink-0 max-lg:hidden"
      >
        <TextContactPanel
          :phone="selectedPhone"
          :title="selectedTitle"
          :message-count="messages.data?.length || 0"
          :last-preview="selectedPreview"
        />
      </div>
    </div>

    <!-- Mobile slide-over uses the same TextContactPanel component -->
    <TextContactPanel
      v-if="selectedPhone"
      overlay
      v-model:open="showContactSheet"
      :phone="selectedPhone"
      :title="selectedTitle"
      :message-count="messages.data?.length || 0"
      :last-preview="selectedPreview"
    />
  </div>
</template>

<script setup>
import FadedScrollableDiv from '@/components/FadedScrollableDiv.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import TextArea from '@/components/Text/TextArea.vue'
import TextBox from '@/components/Text/TextBox.vue'
import TextContactPanel from '@/components/Text/TextContactPanel.vue'
import { globalStore } from '@/stores/global'
import { formatDate } from '@/utils'
import {
  Avatar,
  Breadcrumbs,
  Button,
  FormControl,
  LoadingIndicator,
  TextInput,
  createResource,
} from 'frappe-ui'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import LucideSearch from '~icons/lucide/search'

const breadcrumbs = [{ label: __('Text'), route: { name: 'Text Inbox' } }]

const { $socket } = globalStore()
const selectedPhone = ref('')
const showContactSheet = ref(false)
const threadScroll = ref(null)
const search = ref('')
const typeFilter = ref('All')
const linkFilter = ref('All')

const typeFilterOptions = [
  { label: __('All'), value: 'All' },
  { label: __('Incoming'), value: 'Incoming' },
  { label: __('Outgoing'), value: 'Outgoing' },
]

const linkFilterOptions = [
  { label: __('All links'), value: 'All' },
  { label: __('Lead'), value: 'CRM Lead' },
  { label: __('Deal'), value: 'CRM Deal' },
  { label: __('Contact'), value: 'Contact' },
  { label: __('Unlinked'), value: 'Unlinked' },
]

const smsEnabledResource = createResource({
  url: 'crm.api.sms.is_sms_enabled',
  auto: true,
  cache: 'crm-sms-enabled',
})

const smsEnabled = computed(() => Boolean(smsEnabledResource.data))

const conversations = createResource({
  url: 'crm.api.sms.list_conversations',
  auto: true,
  cache: 'crm-sms-conversations',
})

const messages = createResource({
  url: 'crm.api.sms.get_messages',
  makeParams() {
    return { phone: selectedPhone.value }
  },
})

const selectedConversation = computed(() =>
  (conversations.data || []).find((c) => c.phone === selectedPhone.value),
)

const selectedTitle = computed(
  () => selectedConversation.value?.title || selectedPhone.value,
)

const selectedPreview = computed(
  () => selectedConversation.value?.preview || '',
)

const filteredConversations = computed(() => {
  const q = search.value.trim().toLowerCase()
  return (conversations.data || []).filter((row) => {
    if (typeFilter.value !== 'All' && row.type !== typeFilter.value) {
      return false
    }
    if (linkFilter.value === 'Unlinked') {
      if (row.reference_doctype) return false
    } else if (
      linkFilter.value !== 'All' &&
      row.reference_doctype !== linkFilter.value
    ) {
      return false
    }
    if (!q) return true
    const haystack = [row.title, row.phone, row.preview]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return haystack.includes(q)
  })
})

function selectConversation(phone) {
  selectedPhone.value = phone
  showContactSheet.value = false
}

function onSent() {
  messages.reload()
  conversations.reload()
  scrollThreadToBottom()
}

function scrollThreadToBottom() {
  nextTick(() => {
    const el = threadScroll.value?.$el || threadScroll.value
    if (el?.scrollHeight != null) {
      el.scrollTop = el.scrollHeight
    }
  })
}

watch(selectedPhone, (phone) => {
  if (!phone) {
    showContactSheet.value = false
    return
  }
  messages.reload()
  scrollThreadToBottom()
})

// Open the first conversation so the 3-column layout (incl. contact panel) is visible
watch(
  () => conversations.data,
  (rows) => {
    if (!selectedPhone.value && rows?.length) {
      selectedPhone.value = rows[0].phone
    }
  },
  { immediate: true },
)

watch(
  () => messages.data,
  () => scrollThreadToBottom(),
)

function onSmsRealtime(data) {
  conversations.reload()
  if (
    selectedPhone.value &&
    data?.phone &&
    String(data.phone)
      .replace(/\D/g, '')
      .endsWith(String(selectedPhone.value).replace(/\D/g, '').slice(-10))
  ) {
    messages.reload()
  } else if (selectedPhone.value) {
    messages.reload()
  }
}

onMounted(() => {
  $socket.on('sms_message', onSmsRealtime)
})

onBeforeUnmount(() => {
  $socket.off('sms_message', onSmsRealtime)
})
</script>
