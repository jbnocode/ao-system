<template>
  <Teleport to="body">
    <TransitionRoot :show="showAiSidebar" as="template">
      <div class="fixed inset-0 z-50 flex justify-end">
        <TransitionChild
          as="template"
          enter="transition-opacity ease-linear duration-200"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="transition-opacity ease-linear duration-200"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div
            class="absolute inset-0 bg-black/20"
            aria-hidden="true"
            @click="closeAiSidebar"
          />
        </TransitionChild>
        <TransitionChild
          as="template"
          enter="transform transition ease-in-out duration-300"
          enter-from="translate-x-full"
          enter-to="translate-x-0"
          leave="transform transition ease-in-out duration-300"
          leave-from="translate-x-0"
          leave-to="translate-x-full"
        >
          <div class="relative flex h-full justify-end">
            <aside
              class="flex h-full border-l border-outline-gray-2 bg-surface-base shadow-xl transition-[width] duration-300 ease-in-out"
              :class="
                historyOpen ? 'w-[min(100%,36rem)]' : 'w-[min(100%,24rem)]'
              "
              role="dialog"
              :aria-label="__('AI Assistant')"
            >
              <div
                class="h-full shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out"
                :class="historyOpen ? 'w-48' : 'w-0'"
                :aria-hidden="!historyOpen"
              >
                <AiChatHistory
                  compact
                  class="h-full w-48 transition-transform duration-300 ease-in-out will-change-transform"
                  :class="
                    historyOpen ? 'translate-x-0' : 'translate-x-full'
                  "
                />
              </div>
              <AiChatThread
                class="min-h-0 w-96 min-w-0 shrink-0 grow"
                show-chrome
                context-type="general"
                :empty-hint="
                  __(
                    'Ask about leads, deals, or CRM workflows. Demo mode works without an API key.',
                  )
                "
                :placeholder="__('Ask anything…')"
                @new-chat="newChatSession"
              >
                <template #title-actions>
                  <Button
                    variant="ghost"
                    :icon="
                      historyOpen
                        ? 'lucide-chevron-up'
                        : 'lucide-chevron-down'
                    "
                    :aria-label="
                      historyOpen
                        ? __('Hide chat history')
                        : __('Show chat history')
                    "
                    @click="historyOpen = !historyOpen"
                  />
                </template>
                <template #header-actions>
                  <Button
                    icon="lucide-x"
                    variant="ghost"
                    :aria-label="__('Close')"
                    @click="closeAiSidebar"
                  />
                </template>
              </AiChatThread>
            </aside>
          </div>
        </TransitionChild>
      </div>
    </TransitionRoot>
  </Teleport>
</template>

<script setup>
import AiChatHistory from '@/components/AI/AiChatHistory.vue'
import AiChatThread from '@/components/AI/AiChatThread.vue'
import {
  closeAiSidebar,
  newChatSession,
  showAiSidebar,
} from '@/composables/aiChat'
import { TransitionRoot, TransitionChild } from '@headlessui/vue'
import { Button } from 'frappe-ui'
import { ref } from 'vue'

const historyOpen = ref(true)
</script>
