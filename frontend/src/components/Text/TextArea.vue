<template>
  <div>
    <div
      v-for="sms in messages"
      :key="sms.name"
      class="activity group mb-3 flex gap-2"
      :class="sms.type == 'Outgoing' ? 'flex-row-reverse' : ''"
    >
      <div
        :id="sms.name"
        class="relative max-w-[90%] rounded-5 bg-surface-gray-1 p-1.5 pl-2 text-base text-ink-gray-9 shadow-sm"
      >
        <Badge
          v-if="sms.status == 'Failed'"
          theme="red"
          :label="sms.status"
          class="absolute -top-2 right-0"
        />
        <div class="flex items-end gap-1.5">
          <div class="whitespace-pre-wrap break-words">{{ sms.message }}</div>
          <div class="-mb-1 flex shrink-0 items-end gap-1 text-ink-gray-5">
            <Tooltip :text="formatDate(sms.creation, 'ddd, MMM D, YYYY')">
              <div class="text-2xs">
                {{ formatDate(sms.creation, 'hh:mm a') }}
              </div>
            </Tooltip>
            <div v-if="sms.type == 'Outgoing'">
              <CheckIcon
                v-if="['Queued', 'Sent'].includes(sms.status)"
                class="size-4"
              />
              <DoubleCheckIcon
                v-else-if="sms.status == 'Delivered'"
                class="size-4 text-ink-blue-5"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import CheckIcon from '@/components/Icons/CheckIcon.vue'
import DoubleCheckIcon from '@/components/Icons/DoubleCheckIcon.vue'
import { formatDate } from '@/utils'
import { Badge, Tooltip } from 'frappe-ui'

defineProps({
  messages: { type: Array, default: () => [] },
})
</script>
