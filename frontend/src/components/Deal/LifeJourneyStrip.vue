<template>
  <div
    v-if="snapshot"
    class="mx-5 mb-3 mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-outline-gray-modals bg-surface-gray-1 px-3 py-2.5 text-p-sm"
  >
    <div class="font-medium text-ink-gray-8">{{ __('Life journey') }}</div>
    <div class="flex flex-wrap gap-2 text-ink-gray-6">
      <button class="hover:text-ink-gray-9" @click="$emit('open-tab', 'Quotes')">
        {{ snapshot.counts.quotes }} {{ __('quotes') }}
      </button>
      <span class="text-ink-gray-4">·</span>
      <button
        class="hover:text-ink-gray-9"
        @click="$emit('open-tab', 'Applications')"
      >
        {{ snapshot.counts.applications }} {{ __('apps') }}
      </button>
      <span class="text-ink-gray-4">·</span>
      <button
        class="hover:text-ink-gray-9"
        @click="$emit('open-tab', 'Policies')"
      >
        {{ snapshot.counts.policies }} {{ __('policies') }}
      </button>
    </div>
    <div
      v-if="snapshot.next_action"
      class="ml-auto flex flex-wrap items-center gap-2"
    >
      <span class="text-ink-gray-5">{{ snapshot.next_action.label }}</span>
      <Button
        v-if="snapshot.next_action.set_status"
        size="sm"
        variant="solid"
        :label="__('Apply')"
        :loading="busy"
        @click="applyStatus(snapshot.next_action.set_status)"
      />
      <Button
        v-else-if="snapshot.next_action.quote"
        size="sm"
        variant="solid"
        :label="__('Convert')"
        :loading="busy"
        @click="convertQuote(snapshot.next_action.quote)"
      />
      <Button
        v-else-if="snapshot.next_action.application"
        size="sm"
        variant="solid"
        :label="__('Convert')"
        :loading="busy"
        @click="convertApp(snapshot.next_action.application)"
      />
      <Button
        v-else-if="snapshot.next_action.tab"
        size="sm"
        :label="__('Go')"
        @click="$emit('open-tab', snapshot.next_action.tab)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button, call, createResource, toast } from 'frappe-ui'

const props = defineProps({
  deal: { type: String, required: true },
  reloadKey: { type: [Number, String], default: 0 },
})
const emit = defineEmits(['open-tab', 'updated'])

const busy = ref(false)

const journey = createResource({
  url: 'crm.life.api.get_journey',
  params: { deal: props.deal },
  auto: true,
})

const snapshot = computed(() => journey.data)

watch(
  () => [props.deal, props.reloadKey],
  () => {
    journey.update({ params: { deal: props.deal } })
    journey.reload()
  },
)

async function applyStatus(status) {
  busy.value = true
  try {
    await call('crm.life.api.set_deal_status', { deal: props.deal, status })
    toast.success(__('Deal moved to {0}', [status]))
    journey.reload()
    emit('updated')
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Failed'))
  } finally {
    busy.value = false
  }
}

async function convertQuote(quote) {
  busy.value = true
  try {
    const r = await call('crm.life.api.convert_quote_to_application', { quote })
    toast.success(__('Application {0} created', [r.application]))
    journey.reload()
    emit('updated')
    emit('open-tab', 'Applications')
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Failed'))
  } finally {
    busy.value = false
  }
}

async function convertApp(application) {
  busy.value = true
  try {
    const r = await call('crm.life.api.convert_application_to_policy', {
      application,
    })
    toast.success(__('Policy {0} created', [r.policy]))
    journey.reload()
    emit('updated')
    emit('open-tab', 'Policies')
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Failed'))
  } finally {
    busy.value = false
  }
}

defineExpose({ reload: () => journey.reload() })
</script>
