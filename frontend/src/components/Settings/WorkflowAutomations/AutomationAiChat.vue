<template>
  <div class="flex h-full min-h-0 flex-col">
    <div
      class="flex h-12 shrink-0 items-center border-b border-outline-gray-2 px-3 text-base-semibold text-ink-gray-8"
    >
      {{ __('AI Builder') }}
    </div>
    <AiChatThread
      class="min-h-0 flex-1"
      context-type="automation_builder"
      :snapshot="snapshot"
      can-apply
      :empty-hint="
        __(
          'Try “follow up after 2 days” or “when status becomes Qualified create a task”, then Apply.',
        )
      "
      :placeholder="__('Describe the automation…')"
      @apply="$emit('apply', $event)"
    />
  </div>
</template>

<script setup>
import AiChatThread from '@/components/AI/AiChatThread.vue'

defineProps({
  snapshot: { type: Function, required: true },
})

defineEmits(['apply'])
</script>
