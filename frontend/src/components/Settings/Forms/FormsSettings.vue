<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <FormsList
      v-if="screen === 'list'"
      ref="listRef"
      :hide-page-header="asPage"
      @open="openBuilder"
    />
    <FormBuilderPanel
      v-else
      :key="activeName"
      :name="activeName"
      @back="backToList"
      @saved="() => listRef?.reload?.()"
    />
  </div>
</template>

<script setup>
import { ref, nextTick, computed } from 'vue'
import FormsList from './FormsList.vue'
import FormBuilderPanel from './FormBuilderPanel.vue'

defineProps({
  /** Full-page mode: title/New live in LayoutHeader instead of the body. */
  asPage: { type: Boolean, default: false },
})

const screen = ref('list')
const activeName = ref(null)
const listRef = ref(null)

function openBuilder(name) {
  activeName.value = name
  screen.value = 'builder'
}
async function backToList() {
  screen.value = 'list'
  await nextTick()
  listRef.value?.reload?.()
}

function openCreate() {
  listRef.value?.openCreate?.()
}

function openTemplateLibrary() {
  listRef.value?.openTemplateLibrary?.()
}

const createMenuOptions = computed(
  () => listRef.value?.createMenuOptions ?? [],
)

defineExpose({ openCreate, openTemplateLibrary, screen, createMenuOptions })
</script>
