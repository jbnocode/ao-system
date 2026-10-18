<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="breadcrumbs" />
    </template>
    <template #right-header>
      <Dropdown
        v-if="page?.screen !== 'builder'"
        :options="createMenuOptions"
      >
        <Button
          :label="__('New')"
          variant="solid"
          icon-left="lucide-plus"
          icon-right="lucide-chevron-down"
        />
      </Dropdown>
    </template>
  </LayoutHeader>
  <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
    <WorkflowAutomationPage ref="page" as-page class="min-h-0 flex-1" />
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import WorkflowAutomationPage from '@/components/Settings/WorkflowAutomations/WorkflowAutomationPage.vue'
import { Breadcrumbs, Button, Dropdown } from 'frappe-ui'
import { computed, ref } from 'vue'

const page = ref(null)
const breadcrumbs = [
  { label: __('Automations'), route: { name: 'Automations' } },
]

const createMenuOptions = computed(() => [
  {
    group: __('Create'),
    hideLabel: true,
    options: [
      {
        label: __('New automation'),
        icon: 'lucide-plus',
        onClick: () => page.value?.newAutomation?.(),
      },
      {
        label: __('Templates'),
        icon: 'lucide-layout-template',
        onClick: () => page.value?.openTemplateLibrary?.(),
      },
    ],
  },
])
</script>
