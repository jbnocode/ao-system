<template>
  <TelephonySettings
    v-if="step === 'telephony-settings'"
    @updateStep="updateStep"
  />
  <TwilioSettings
    v-else-if="step === 'twilio-settings'"
    @updateStep="updateStep"
  />
  <ExotelSettings
    v-else-if="step === 'exotel-settings'"
    @updateStep="updateStep"
  />
</template>
<script setup>
import { telephonySettingsStep } from '@/composables/settings'
import TelephonySettings from './TelephonySettings.vue'
import ExotelSettings from './ExotelSettings.vue'
import TwilioSettings from './TwilioSettings.vue'
import { usersStore } from '@/stores/users'
import { onMounted, ref, watch } from 'vue'

const { isAdmin } = usersStore()
const step = ref('telephony-settings')

const adminOnlySteps = new Set(['twilio-settings', 'exotel-settings'])

function resolveStep(next) {
  if (next === 'phone-numbers') return 'telephony-settings'
  if (adminOnlySteps.has(next) && !isAdmin()) {
    return 'telephony-settings'
  }
  return next
}

function applyInitialStep() {
  if (telephonySettingsStep.value) {
    step.value = resolveStep(telephonySettingsStep.value)
    telephonySettingsStep.value = ''
  }
}

onMounted(applyInitialStep)
watch(telephonySettingsStep, applyInitialStep)

function updateStep(newStep) {
  step.value = resolveStep(newStep)
}
</script>
