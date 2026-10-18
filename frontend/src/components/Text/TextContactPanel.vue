<template>
  <!-- Desktop: docked resizable sidebar -->
  <Resizer
    v-if="!overlay"
    ref="resizerRef"
    side="right"
    class="flex h-full flex-col overflow-hidden bg-surface-base"
    collapsible
    collapsed-storage-key="textContactPanelCollapsed"
    width-storage-key="textContactPanelWidth"
    v-slot="{ collapse }"
  >
    <TextContactDetails
      class="h-full bg-surface-base"
      :phone="phone"
      :title="title"
      :message-count="messageCount"
      :last-preview="lastPreview"
      :collapse="collapse"
    />
  </Resizer>

  <!-- Mobile: slide-over sidebar -->
  <Teleport v-else to="body">
    <TransitionRoot :show="open" as="template">
      <div class="fixed inset-0 z-50 flex justify-end lg:hidden">
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
            @click="emit('update:open', false)"
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
          <aside
            class="relative z-10 flex h-full w-[min(100%,24rem)] flex-col border-l border-outline-gray-modals bg-surface-base shadow-xl"
            role="dialog"
            :aria-label="__('Contact details')"
          >
            <TextContactDetails
              class="h-full bg-surface-base"
              :phone="phone"
              :title="title"
              :message-count="messageCount"
              :last-preview="lastPreview"
              show-close
              @close="emit('update:open', false)"
            />
          </aside>
        </TransitionChild>
      </div>
    </TransitionRoot>
  </Teleport>
</template>

<script setup>
import Resizer from '@/components/Resizer.vue'
import TextContactDetails from '@/components/Text/TextContactDetails.vue'
import { TransitionChild, TransitionRoot } from '@headlessui/vue'
import { onMounted, ref } from 'vue'

defineProps({
  phone: { type: String, default: '' },
  title: { type: String, default: '' },
  messageCount: { type: Number, default: 0 },
  lastPreview: { type: String, default: '' },
  /** When true, render as a mobile slide-over instead of the docked Resizer. */
  overlay: { type: Boolean, default: false },
  /** Controls overlay visibility (v-model:open). Ignored when overlay is false. */
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open'])

const resizerRef = ref(null)

onMounted(() => {
  if (!resizerRef.value) return
  localStorage.setItem('textContactPanelCollapsed', '0')
  resizerRef.value.expand?.()
})
</script>
