<template>
  <div class="flex min-h-0 flex-1 flex-col overflow-y-auto bg-surface-white">
    <div class="mx-auto flex w-full max-w-2xl flex-col gap-6 px-5 py-10">
      <div class="text-center">
        <h1 class="text-2xl-semibold text-ink-gray-9">
          {{ greeting }}
        </h1>
        <p class="mt-2 text-p-base text-ink-gray-6">
          {{
            __(
              'Build talk tracks, test your agent, or place outbound AI calls — without a setup wizard.',
            )
          }}
        </p>
      </div>

      <div
        v-if="!hasAssignment"
        class="rounded-5 border border-outline-gray-modals bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-7"
      >
        {{
          __(
            'No AI number linked yet. Ask a manager to assign one under Settings → AI Caller.',
          )
        }}
      </div>
      <div
        v-else
        class="rounded-5 border border-outline-gray-modals bg-surface-gray-1 px-4 py-3 text-p-sm text-ink-gray-7"
      >
        {{ __('Assigned number') }}:
        <span class="font-medium text-ink-gray-9">{{
          assignment?.phone_number
        }}</span>
      </div>

      <div class="grid gap-2 sm:grid-cols-2">
        <button
          v-for="chip in chips"
          :key="chip.id"
          type="button"
          class="flex items-start gap-3 rounded-5 border border-outline-gray-modals px-4 py-3 text-left transition hover:bg-surface-gray-1"
          @click="$emit('action', chip.id)"
        >
          <component
            :is="chip.icon"
            class="mt-0.5 size-4 shrink-0 text-ink-gray-6"
          />
          <div class="min-w-0">
            <div class="text-p-base-medium text-ink-gray-8">
              {{ chip.label }}
            </div>
            <div class="mt-0.5 text-p-sm text-ink-gray-5">
              {{ chip.description }}
            </div>
          </div>
        </button>
      </div>

      <form
        class="rounded-5 border border-outline-gray-2 bg-surface-white"
        @submit.prevent="submit"
      >
        <Textarea
          v-model="draft"
          variant="ghost"
          size="sm"
          :rows="3"
          class="w-full resize-none"
          :placeholder="__('What would you like to build?')"
          :aria-label="__('What would you like to build?')"
        />
        <div class="flex items-center justify-end gap-1 px-2.5 pb-2.5">
          <Button
            type="submit"
            variant="solid"
            size="sm"
            :label="__('Continue')"
            :disabled="!draft.trim()"
          />
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { Button, Textarea } from 'frappe-ui'
import { computed, ref } from 'vue'
import LucideBot from '~icons/lucide/bot'
import LucideBug from '~icons/lucide/bug'
import LucideChartColumn from '~icons/lucide/chart-column'
import LucideFlaskConical from '~icons/lucide/flask-conical'
import LucidePhoneCall from '~icons/lucide/phone-call'

const props = defineProps({
  firstName: { type: String, default: '' },
  assignment: { type: Object, default: null },
  isManager: { type: Boolean, default: false },
})

const emit = defineEmits(['action', 'prompt'])

const draft = ref('')

const hasAssignment = computed(() =>
  Boolean(props.assignment?.phone_number && props.assignment?.vapi_assistant_id),
)

const greeting = computed(() => {
  const name = (props.firstName || '').trim()
  return name
    ? __('Hey {0}, how can I help?', [name])
    : __('Hey, how can I help?')
})

const chips = computed(() => {
  const items = [
    {
      id: 'assistants',
      label: __('Build'),
      description: __('Review voice, script, and compliance for your agent.'),
      icon: LucideBot,
    },
    {
      id: 'dialer',
      label: __('Outbound'),
      description: __('Call hot leads with your assigned AI number.'),
      icon: LucidePhoneCall,
    },
    {
      id: 'test-agent',
      label: __('Test'),
      description: __('Talk to your agent in the browser before dialing out.'),
      icon: LucideFlaskConical,
    },
  ]
  if (props.isManager) {
    items.push({
      id: 'usage',
      label: __('Analyze'),
      description: __('Review team AI caller usage and recent activity.'),
      icon: LucideChartColumn,
    })
  }
  items.push({
    id: 'phone-numbers',
    label: __('Debug'),
    description: __('Check assignment status if calls are failing.'),
    icon: LucideBug,
  })
  return items
})

function submit() {
  const text = draft.value.trim()
  if (!text) return
  emit('prompt', text)
  draft.value = ''
  emit('action', 'assistants')
}
</script>
