<template>
  <LayoutHeader>
    <template #left-header>
      <Breadcrumbs :items="breadcrumbs" />
    </template>
  </LayoutHeader>
  <div class="flex-1 overflow-y-auto">
    <WorkflowAutomationPage />
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import WorkflowAutomationPage from '@/components/Settings/WorkflowAutomations/WorkflowAutomationPage.vue'
import { Breadcrumbs } from 'frappe-ui'

const breadcrumbs = [{ label: __('Automations'), route: { name: 'Automations' } }]
</script>
