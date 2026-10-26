<template>
  <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5">
    <h2 class="text-xl-semibold text-ink-gray-9">
      {{ __('Phone Numbers') }}
    </h2>
    <p class="mt-1 max-w-xl text-p-sm text-ink-gray-5">
      {{
        __(
          'Managers assign numbers in Settings. Agents use the number linked for AI outbound.',
        )
      }}
    </p>

    <div class="mt-6 max-w-lg space-y-4">
      <div v-if="assignment?.phone_number">
        <div class="text-p-sm text-ink-gray-5">{{ __('Your AI number') }}</div>
        <div class="mt-1 text-lg-semibold text-ink-gray-9">
          {{ assignment.phone_number }}
        </div>
        <div class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('Ready for GPT-Live AI calls') }}
        </div>
      </div>
      <div v-else class="text-p-base text-ink-gray-6">
        {{ __('No number assigned to you yet.') }}
      </div>

      <div class="flex flex-wrap gap-2">
        <Button
          variant="subtle"
          icon-left="lucide-refresh-cw"
          :label="__('Refresh')"
          :loading="loading"
          @click="$emit('refresh')"
        />
        <Button
          v-if="isManager"
          variant="solid"
          :label="__('Manage numbers')"
          @click="$emit('open-settings')"
        />
        <Button
          variant="subtle"
          :label="__('Human dialer')"
          @click="$emit('human-dialer')"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'

defineProps({
  assignment: { type: Object, default: null },
  isManager: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

defineEmits(['refresh', 'open-settings', 'human-dialer'])
</script>
