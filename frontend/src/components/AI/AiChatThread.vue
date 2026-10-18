<template>
  <div class="flex h-full min-h-0 flex-col bg-surface-white">
    <div
      v-if="showChrome"
      class="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-outline-gray-modals px-4"
    >
      <div class="flex min-w-0 items-center gap-1">
        <div class="min-w-0 truncate text-base-semibold text-ink-gray-8">
          {{ title || __('New chat') }}
        </div>
        <slot name="title-actions" />
      </div>
      <div class="flex shrink-0 items-center gap-0.5">
        <Button
          variant="ghost"
          icon="lucide-plus"
          :aria-label="__('New chat')"
          @click="$emit('new-chat')"
        />
        <Dropdown :options="moreOptions">
          <Button
            variant="ghost"
            icon="lucide-more-horizontal"
            :aria-label="__('More')"
          />
        </Dropdown>
        <slot name="header-actions" />
      </div>
    </div>

    <div ref="scroller" class="min-h-0 flex-1 overflow-y-auto">
      <div class="mx-auto flex w-full max-w-2xl flex-col gap-4 px-4 py-6">
        <div
          v-if="!messages.length && !loading"
          class="rounded-5 border border-outline-gray-modals bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-6"
        >
          {{ emptyHint || __('Ask anything about your CRM…') }}
        </div>

        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="flex gap-3"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            v-if="msg.role !== 'user'"
            class="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-7"
          >
            <LucideSparkles class="size-3.5" />
          </div>
          <div
            class="min-w-0 text-p-sm"
            :class="[
              msg.blocks?.length ? 'max-w-full' : 'max-w-[85%]',
              msg.role === 'user'
                ? 'rounded-5 bg-black px-3.5 py-2.5 text-ink-white whitespace-pre-wrap'
                : 'rounded-5 bg-surface-gray-1 px-3.5 py-2.5 text-ink-gray-8',
            ]"
          >
            <div class="whitespace-pre-wrap">{{ msg.content }}</div>
            <template v-for="(block, bi) in msg.blocks || []" :key="bi">
              <AiInsuranceBlock
                v-if="block.type === 'insurance'"
                :block="block"
              />
              <div v-else-if="block.type === 'table'" class="mt-3 overflow-x-auto">
                <div
                  v-if="block.title"
                  class="mb-1.5 text-p-sm-medium text-ink-gray-7"
                >
                  {{ block.title }}
                </div>
                <table
                  class="w-full min-w-[28rem] border-collapse text-left text-p-sm"
                >
                  <thead>
                    <tr class="border-b border-outline-gray-modals">
                      <th
                        v-for="(col, ci) in block.columns"
                        :key="ci"
                        class="px-2 py-1.5 font-medium text-ink-gray-6"
                      >
                        {{ col }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="(row, ri) in block.rows"
                      :key="ri"
                      class="border-b border-outline-gray-1 last:border-0"
                    >
                      <td
                        v-for="(cell, ci) in row"
                        :key="ci"
                        class="px-2 py-1.5 text-ink-gray-8"
                      >
                        {{ cell }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
            <div
              v-if="msg.ops?.length"
              class="mt-2 flex flex-wrap gap-1 border-t border-outline-gray-2 pt-2"
            >
              <Badge
                v-for="(op, j) in msg.ops"
                :key="j"
                :label="op.op"
                theme="blue"
                variant="subtle"
              />
              <Button
                v-if="canApply && msg.ops?.length"
                class="mt-1"
                size="sm"
                variant="solid"
                :label="__('Apply to canvas')"
                @click="$emit('apply', msg.ops)"
              />
            </div>
          </div>
        </div>

        <div v-if="loading" class="flex items-start gap-3">
          <div
            class="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-7"
          >
            <LucideSparkles class="size-3.5" />
          </div>
          <div
            class="rounded-5 bg-surface-gray-1 px-3.5 py-2.5 text-p-sm text-ink-gray-5"
          >
            <span class="inline-flex items-center gap-1">
              <span
                class="size-1.5 animate-pulse rounded-full bg-ink-gray-4"
              />
              <span
                class="size-1.5 animate-pulse rounded-full bg-ink-gray-4 [animation-delay:150ms]"
              />
              <span
                class="size-1.5 animate-pulse rounded-full bg-ink-gray-4 [animation-delay:300ms]"
              />
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="shrink-0 border-t border-outline-gray-modals bg-surface-white p-4">
      <form
        class="mx-auto max-w-2xl rounded-5 border border-outline-gray-2 bg-surface-white"
        @submit.prevent="send"
      >
        <Textarea
          v-model="draft"
          variant="ghost"
          size="sm"
          :rows="2"
          class="w-full resize-none"
          :placeholder="placeholder || __('Ask anything…')"
          :disabled="loading"
          :aria-label="placeholder || __('Ask anything…')"
          @keydown.enter.exact.prevent="send"
        />
        <div class="flex items-center justify-end gap-1 px-2.5 pb-2.5">
          <Button
            type="button"
            size="sm"
            :variant="listening ? 'subtle' : 'ghost'"
            icon="lucide-mic"
            :aria-label="
              listening ? __('Stop listening') : __('Speech to text')
            "
            :disabled="loading"
            :class="listening ? 'text-ink-red-4' : ''"
            @click="toggleListening"
          />
          <Button
            type="submit"
            variant="solid"
            size="sm"
            :label="__('Send')"
            :loading="loading"
            :disabled="!draft.trim()"
          />
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import {
  activeSession,
  activeSessionId,
  clearActiveChat,
  deleteActiveChat,
  setSessionMessages,
} from '@/composables/aiChat'
import { useSpeechToText } from '@/composables/useSpeechToText'
import AiInsuranceBlock from '@/components/AI/AiInsuranceBlock.vue'
import { normalizeChatBlocks } from '@/utils/aiChatBlocks'
import { Badge, Button, Dropdown, Textarea, call, toast } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'
import LucideSparkles from '~icons/lucide/sparkles'

const props = defineProps({
  contextType: { type: String, default: 'general' },
  snapshot: { type: Function, default: null },
  canApply: { type: Boolean, default: false },
  emptyHint: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  showChrome: { type: Boolean, default: false },
  modelLabel: { type: String, default: '' },
  /** When set, send once after mount / change (AI home → chat). */
  initialPrompt: { type: String, default: '' },
})

defineEmits(['apply', 'new-chat', 'status-click', 'attach'])

const messages = ref([])
const draft = ref('')
const loading = ref(false)
const scroller = ref(null)

const { listening, toggle: toggleListening, stop: stopListening } =
  useSpeechToText(draft)

const title = computed(
  () => activeSession.value?.title || props.modelLabel || __('New chat'),
)

const moreOptions = computed(() => [
  {
    label: __('Clear chat'),
    icon: 'lucide-refresh-cw',
    onClick: () => {
      clearActiveChat()
      messages.value = []
    },
  },
  {
    label: __('Delete chat'),
    icon: 'lucide-trash-2',
    onClick: () => {
      deleteActiveChat()
    },
  },
])

watch(
  activeSessionId,
  () => {
    messages.value = [...(activeSession.value?.messages || [])]
    scrollBottom()
  },
  { immediate: true },
)

watch(
  () => props.initialPrompt,
  (prompt) => {
    const text = (prompt || '').trim()
    if (!text || loading.value) return
    sendPrompt(text)
  },
)

async function send() {
  await sendPrompt(draft.value)
}

/** Send a prompt from outside (e.g. AI home chips). */
async function sendPrompt(text) {
  const content = String(text || '').trim()
  if (!content || loading.value) return
  stopListening()
  messages.value.push({ role: 'user', content })
  draft.value = ''
  setSessionMessages(messages.value)
  loading.value = true
  scrollBottom()
  try {
    const context = { type: props.contextType }
    if (props.snapshot) {
      const snap = props.snapshot()
      if (snap) {
        context.snapshot = snap
        if (props.contextType === 'home') context.briefing = snap
      }
    }
    const res = await call('crm.ai.chat.chat', {
      messages: messages.value.map(({ role, content }) => ({ role, content })),
      context,
    })
    messages.value.push({
      role: 'assistant',
      content: res.reply || __('Done.'),
      ops: res.ops || [],
      blocks: normalizeChatBlocks(res.blocks),
    })
    setSessionMessages(messages.value)
  } catch (e) {
    toast.error(
      e?.messages?.join?.(' ') || e?.message || __('AI request failed'),
    )
    messages.value.push({
      role: 'assistant',
      content: e?.messages?.[0] || e?.message || __('Something went wrong.'),
    })
    setSessionMessages(messages.value)
  } finally {
    loading.value = false
    scrollBottom()
  }
}

function scrollBottom() {
  nextTick(() => {
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  })
}

defineExpose({ messages, sendPrompt })
</script>
