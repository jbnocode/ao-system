<template>
  <nav
    class="flex h-full w-[200px] shrink-0 flex-col overflow-y-auto border-r border-outline-gray-modals bg-surface-gray-1 px-2 py-3"
    aria-label="AI Caller"
  >
    <div
      v-for="section in sections"
      :key="section.id"
      class="mb-3"
    >
      <div
        class="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-ink-gray-5"
      >
        {{ section.label }}
      </div>
      <div class="flex flex-col gap-0.5">
        <button
          v-for="item in section.items"
          :key="item.id"
          type="button"
          class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-p-sm transition"
          :class="
            modelValue === item.id
              ? 'bg-surface-gray-3 text-ink-gray-9 font-medium'
              : 'text-ink-gray-7 hover:bg-surface-gray-2'
          "
          @click="onSelect(item)"
        >
          <component
            :is="item.icon"
            class="size-4 shrink-0 text-ink-gray-6"
          />
          <span class="min-w-0 truncate">{{ item.label }}</span>
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import LucideBot from '~icons/lucide/bot'
import LucideFlaskConical from '~icons/lucide/flask-conical'
import LucideLayoutDashboard from '~icons/lucide/layout-dashboard'
import LucidePhone from '~icons/lucide/phone'
import LucidePhoneCall from '~icons/lucide/phone-call'
import LucideScrollText from '~icons/lucide/scroll-text'
import LucideSparkles from '~icons/lucide/sparkles'
import LucideMegaphone from '~icons/lucide/megaphone'

const props = defineProps({
  modelValue: { type: String, default: 'composer' },
  isManager: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'navigate'])

const sections = computed(() => {
  const observeItems = [
    {
      id: 'call-logs',
      label: __('Call logs'),
      icon: LucideScrollText,
    },
  ]
  if (props.isManager) {
    observeItems.push({
      id: 'usage',
      label: __('Usage'),
      icon: LucideLayoutDashboard,
      route: 'AI Caller Usage',
    })
  }

  return [
    {
      id: 'labs',
      label: __('Labs'),
      items: [
        {
          id: 'composer',
          label: __('Assistant'),
          icon: LucideSparkles,
        },
      ],
    },
    {
      id: 'build',
      label: __('Build'),
      items: [
        { id: 'assistants', label: __('AI Agent'), icon: LucideBot },
        { id: 'phone-numbers', label: __('Phone Numbers'), icon: LucidePhone },
        { id: 'dialer', label: __('Outbound'), icon: LucidePhoneCall },
        {
          id: 'campaigns',
          label: __('Campaigns'),
          icon: LucideMegaphone,
          route: 'Campaigns',
        },
      ],
    },
    {
      id: 'test',
      label: __('Test'),
      items: [
        {
          id: 'test-agent',
          label: __('Test agent'),
          icon: LucideFlaskConical,
        },
      ],
    },
    {
      id: 'observe',
      label: __('Observe'),
      items: observeItems,
    },
  ]
})

function onSelect(item) {
  if (item.route) {
    emit('navigate', item.route)
    return
  }
  emit('update:modelValue', item.id)
}
</script>
