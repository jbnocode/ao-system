<template>
  <div
    class="min-h-screen bg-surface-gray-1 px-4 py-8 text-ink-gray-8 sm:px-6"
  >
    <div class="mx-auto w-full max-w-lg">
      <div v-if="loading" class="flex justify-center py-20">
        <LoadingIndicator class="w-5" />
      </div>

      <div
        v-else-if="error"
        class="rounded-lg border border-outline-gray-modals bg-surface-white p-6 text-center"
      >
        <div class="text-p-base-medium">{{ error }}</div>
        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __('This booking page may be disabled or the link is wrong.') }}
        </p>
      </div>

      <template v-else-if="profile">
        <div
          v-if="profile.provider === 'Calendly'"
          class="overflow-hidden rounded-lg border border-outline-gray-modals bg-surface-white"
        >
          <div class="border-b border-outline-gray-modals px-4 py-3">
            <div class="text-lg-medium">{{ profile.page_title }}</div>
            <p v-if="profile.agent_name" class="text-p-sm text-ink-gray-5">
              {{ profile.agent_name }}
            </p>
          </div>
          <iframe
            v-if="calendlySrc"
            :src="calendlySrc"
            title="Calendly"
            class="h-[640px] w-full border-0"
          />
          <div v-else class="p-6 text-center">
            <Button
              variant="solid"
              :label="__('Open Calendly')"
              @click="openExternal(profile.calendly_url)"
            />
          </div>
        </div>

        <div
          v-else
          class="rounded-lg border border-outline-gray-modals bg-surface-white p-6 text-center"
        >
          <div class="text-lg-medium">{{ profile.page_title }}</div>
          <p class="mt-1 text-p-sm text-ink-gray-5">
            <span v-if="profile.meeting_provider && profile.meeting_provider !== 'None'">
              {{ profile.meeting_provider }} ·
            </span>
            {{ __('Choose a time on the scheduling page.') }}
          </p>
          <Button
            class="mt-4"
            variant="solid"
            :label="__('Continue')"
            @click="goSchedule"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { Button, LoadingIndicator, call } from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const profile = ref(null)

const calendlySrc = computed(() => {
  const url = (profile.value?.calendly_url || '').trim()
  if (!url) return ''
  try {
    const u = new URL(url)
    u.searchParams.set('embed_domain', window.location.hostname)
    u.searchParams.set('embed_type', 'Inline')
    return u.toString()
  } catch {
    return url
  }
})

function openExternal(url) {
  if (url) window.open(url, '_blank', 'noopener')
}

function goSchedule() {
  const url =
    profile.value?.schedule_url ||
    `/schedule/in/${encodeURIComponent(route.params.slug)}`
  window.location.href = url
}

async function loadProfile() {
  loading.value = true
  error.value = ''
  try {
    const data = await call('crm.api.booking.get_public_booking', {
      slug: route.params.slug,
    })
    profile.value = data
    if (data.provider === 'Native' && data.schedule_url) {
      window.location.replace(data.schedule_url)
      return
    }
  } catch (e) {
    error.value =
      e?.messages?.[0] || e?.message || __('Booking page not found')
  } finally {
    loading.value = false
  }
}

watch(
  () => route.params.slug,
  () => loadProfile(),
)

onMounted(loadProfile)
</script>
