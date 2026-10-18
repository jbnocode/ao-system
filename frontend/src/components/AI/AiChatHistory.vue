<template>
  <aside
    class="flex h-full shrink-0 flex-col bg-surface-white"
    :class="[
      compact ? 'w-48' : 'w-60',
      side === 'right'
        ? 'border-l border-outline-gray-modals'
        : 'border-r border-outline-gray-modals',
    ]"
  >
    <div class="flex flex-col gap-2 border-b border-outline-gray-modals p-3">
      <Button
        class="w-full justify-start"
        variant="subtle"
        icon-left="lucide-plus"
        :label="__('New chat')"
        @click="onNewChat"
      />
      <TextInput
        v-model="chatSearchQuery"
        type="text"
        size="sm"
        :placeholder="__('Search chats')"
      >
        <template #prefix>
          <LucideSearch class="h-4 w-4 text-ink-gray-5" />
        </template>
      </TextInput>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto px-2 py-2">
      <div
        v-if="!sessionGroups.length"
        class="px-2 py-4 text-center text-p-sm text-ink-gray-5"
      >
        {{ __('No chats yet') }}
      </div>
      <div v-for="group in sessionGroups" :key="group.key" class="mb-3">
        <div
          class="px-2 py-1 text-xs font-medium uppercase tracking-wide text-ink-gray-5"
        >
          {{ group.label }}
        </div>
        <div
          v-for="session in group.items"
          :key="session.id"
          class="group/chat mb-0.5 flex w-full items-center rounded-5 text-p-sm text-ink-gray-7 transition-colors hover:bg-surface-gray-2"
          :class="
            session.id === activeSessionId
              ? 'bg-surface-gray-2 text-ink-gray-9'
              : ''
          "
        >
          <button
            type="button"
            class="min-w-0 flex-1 truncate px-2.5 py-2 text-left"
            @click="onSelect(session.id)"
          >
            {{ session.title }}
          </button>
          <Dropdown
            :options="sessionOptions(session)"
            placement="left"
            @update:open="(open) => !open && (confirmingDelete = '')"
          >
            <Button
              class="mr-0.5 shrink-0"
              :class="
                compact
                  ? 'opacity-100'
                  : [
                      'opacity-0 group-hover/chat:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100',
                      session.id === activeSessionId ||
                      confirmingDelete === session.id
                        ? 'opacity-100'
                        : '',
                    ]
              "
              variant="ghost"
              size="sm"
              :aria-label="__('More')"
              @click.stop
            >
              <template #icon>
                <LucideMoreHorizontal
                  class="size-4 text-ink-gray-5"
                />
              </template>
            </Button>
          </Dropdown>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import {
  activeSessionId,
  chatSearchQuery,
  deleteChatSession,
  getSessionShareText,
  newChatSession,
  selectChatSession,
  sessionGroups,
} from '@/composables/aiChat'
import { ConfirmDelete } from '@/utils'
import { Button, Dropdown, TextInput, toast } from 'frappe-ui'
import { ref } from 'vue'
import LucideMoreHorizontal from '~icons/lucide/more-horizontal'
import LucideSearch from '~icons/lucide/search'

defineProps({
  compact: { type: Boolean, default: false },
  side: {
    type: String,
    default: 'left',
    validator: (v) => ['left', 'right'].includes(v),
  },
})

const emit = defineEmits(['new-chat', 'select', 'deleted'])

const confirmingDelete = ref('')

function onNewChat() {
  newChatSession()
  emit('new-chat')
}

function onSelect(id) {
  selectChatSession(id)
  emit('select', id)
}

function sessionOptions(session) {
  const isConfirmingDelete = {
    get value() {
      return confirmingDelete.value === session.id
    },
    set value(v) {
      confirmingDelete.value = v ? session.id : ''
    },
  }
  return [
    {
      group: __('Actions'),
      hideLabel: true,
      options: [
        {
          label: __('Share'),
          icon: 'lucide-share',
          onClick: () => shareSession(session),
        },
        ...ConfirmDelete({
          isConfirmingDelete,
          label: __('Delete'),
          onConfirmDelete: () => {
            deleteChatSession(session.id)
            emit('deleted', session.id)
            toast.success(__('Chat deleted'))
          },
        }),
      ],
    },
  ]
}

async function shareSession(session) {
  const text = getSessionShareText(session.id)
  if (!text) {
    toast.error(__('Nothing to share yet'))
    return
  }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const el = document.createElement('textarea')
      el.value = text
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    toast.success(__('Chat copied to clipboard'))
  } catch {
    toast.error(__('Could not copy chat'))
  }
}
</script>
