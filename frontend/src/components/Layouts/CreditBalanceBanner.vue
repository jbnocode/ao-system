<template>
  <Tooltip
    :text="tooltipText"
    side="right"
    :disabled="!isSidebarCollapsed"
  >
    <SidebarItem :label="__('Credits')" @click="openCredits">
      <template #prefix>
        <LucideCoins class="size-4 text-ink-gray-7" />
      </template>
      <span class="flex-1 truncate text-sm leading-tighter text-ink-gray-7">
        {{ __('Credits') }}
      </span>
      <span
        v-if="!isSidebarCollapsed"
        class="mr-2 text-sm tabular-nums text-ink-gray-7"
      >
        {{ credits }}
      </span>
    </SidebarItem>
  </Tooltip>
</template>

<script setup>
import {
  activeSettingsPage,
  showSettings,
} from '@/composables/settings'
import { usersStore } from '@/stores/users'
import LucideCoins from '~icons/lucide/coins'
import { createResource, SidebarItem, Tooltip } from 'frappe-ui'
import { computed } from 'vue'

defineProps({
  isSidebarCollapsed: { type: Boolean, default: false },
})

const { isManager } = usersStore()

const balance = createResource({
  url: 'crm.ai.credits.get_balance',
  auto: true,
  cache: 'crm-ai-credit-balance',
})

const credits = computed(() => Number(balance.data?.credits ?? 0))

const tooltipText = computed(() =>
  __('Credits: {0}', [credits.value]),
)

function openCredits() {
  if (!isManager()) return
  activeSettingsPage.value = 'Credits'
  showSettings.value = true
}
</script>
