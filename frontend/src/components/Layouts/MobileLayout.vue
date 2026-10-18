<template>
  <div class="flex h-screen w-screen overflow-hidden">
    <MobileSidebar />
    <div
      class="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-surface-base"
    >
      <MobileAppHeader />
      <div class="flex min-h-0 min-w-0 flex-1 flex-col overflow-auto">
        <slot />
      </div>
    </div>
    <GlobalModals />
  </div>
</template>
<script setup>
import MobileSidebar from '@/components/Mobile/MobileSidebar.vue'
import MobileAppHeader from '@/components/Mobile/MobileAppHeader.vue'
import GlobalModals from '@/components/Modals/GlobalModals.vue'
</script>
