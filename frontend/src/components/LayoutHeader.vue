<template>
  <Teleport v-if="showHeader" to="#app-header">
    <slot>
      <div class="flex flex-col">
        <header
          class="flex h-10.5 items-center justify-between py-[7px] sm:pl-5 pl-2"
        >
          <div class="flex min-w-0 items-center gap-2">
            <slot name="left-header" />
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <Button
              variant="solid"
              icon="lucide-sparkles"
              :aria-label="__('AI')"
              @click="toggleAiSidebar"
            />
            <slot name="right-header" />
          </div>
        </header>
        <div
          v-if="slots['below-header']"
          class="flex items-center justify-start gap-2 border-t border-outline-gray-2 py-1.5 pr-2 pl-2 sm:pl-5 sm:pr-0"
        >
          <slot name="below-header" />
        </div>
      </div>
    </slot>
  </Teleport>
</template>
<script setup>
import { toggleAiSidebar } from '@/composables/aiChat'
import { Button } from 'frappe-ui'
import { nextTick, ref, useSlots } from 'vue'

const slots = useSlots()
const showHeader = ref(false)

nextTick(() => {
  showHeader.value = true
})
</script>
