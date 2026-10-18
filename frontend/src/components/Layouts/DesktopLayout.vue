<template>
  <div class="flex h-screen w-screen overflow-hidden">
    <AppSidebar />
    <div
      class="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-surface-base"
    >
      <AppHeader />
      <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-auto">
        <slot />
      </div>
    </div>
    <GlobalModals />
  </div>
</template>
<script setup>
import AppSidebar from '@/components/Layouts/AppSidebar.vue'
import AppHeader from '@/components/Layouts/AppHeader.vue'
import GlobalModals from '@/components/Modals/GlobalModals.vue'
</script>
