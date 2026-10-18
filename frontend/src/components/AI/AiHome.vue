<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-y-auto bg-surface-white">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-5 px-5 py-8">
      <div class="text-center">
        <h1 class="text-2xl-semibold text-ink-gray-8">
          {{ briefing?.greeting || __('Good day.') }}
        </h1>
      </div>

      <form
        class="rounded-5 border border-outline-gray-2 bg-surface-white"
        @submit.prevent="submitDraft"
      >
        <Textarea
          v-model="draft"
          variant="ghost"
          size="sm"
          :rows="3"
          class="w-full resize-none"
          :placeholder="__('Ask anything about your CRM…')"
          :disabled="loading"
          :aria-label="__('Ask anything about your CRM…')"
          @keydown.enter.exact.prevent="submitDraft"
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

      <div
        v-if="briefing?.suggestions?.length"
        class="flex flex-wrap items-center justify-center gap-2"
      >
        <Button
          v-for="chip in briefing.suggestions"
          :key="chip.id"
          size="sm"
          variant="outline"
          :label="chip.label"
          @click="emit('ask', chip.prompt)"
        >
          <template #prefix>
            <LucideCircleAlert
              v-if="chip.icon === 'alert'"
              class="size-3.5 text-ink-amber-5"
            />
            <LucideUsers
              v-else-if="chip.icon === 'users'"
              class="size-3.5 text-ink-gray-5"
            />
            <LucideSparkles
              v-else-if="chip.icon === 'sparkles'"
              class="size-3.5 text-ink-gray-5"
            />
            <LucideListTodo v-else class="size-3.5 text-ink-gray-5" />
          </template>
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSpeechToText } from '@/composables/useSpeechToText'
import { Button, Textarea } from 'frappe-ui'
import { ref, watch } from 'vue'
import LucideCircleAlert from '~icons/lucide/circle-alert'
import LucideListTodo from '~icons/lucide/list-todo'
import LucideSparkles from '~icons/lucide/sparkles'
import LucideUsers from '~icons/lucide/users'

const props = defineProps({
  briefing: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['ask'])

const draft = ref('')
const { listening, toggle: toggleListening, stop: stopListening } =
  useSpeechToText(draft)

watch(
  () => props.loading,
  (v) => {
    if (!v) draft.value = ''
  },
)

function submitDraft() {
  const text = draft.value.trim()
  if (!text || props.loading) return
  stopListening()
  draft.value = ''
  emit('ask', text)
}

defineExpose({ draft })
</script>
