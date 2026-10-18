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
    <FormsSettings ref="page" as-page class="min-h-0 flex-1" />
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import FormsSettings from '@/components/Settings/Forms/FormsSettings.vue'
import { Breadcrumbs, Button, Dropdown } from 'frappe-ui'
import { computed, ref } from 'vue'

const page = ref(null)
const breadcrumbs = [{ label: __('Forms'), route: { name: 'Forms' } }]

const createMenuOptions = computed(() => [
  {
    group: __('Create'),
    hideLabel: true,
    options: [
      {
        label: __('New form'),
        icon: 'lucide-plus',
        onClick: () => page.value?.openCreate?.(),
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
