<template>
  <Dialog v-model:open="open" :title="__('Deal assistant')" @close="open = false">
    <template #default>
      <div class="flex max-h-[70vh] flex-col gap-4 overflow-y-auto">
        <div v-if="loading" class="flex items-center gap-2 text-p-sm text-ink-gray-5">
          <LoadingIndicator class="h-4 w-4" />
          {{ __('Loading case context…') }}
        </div>
        <template v-else-if="overview">
          <div class="rounded-lg bg-surface-gray-1 p-3 text-p-sm text-ink-gray-8 whitespace-pre-wrap">
            {{ overview.summary }}
          </div>

          <div>
            <div class="mb-2 text-p-sm-medium text-ink-gray-7">
              {{ __('Suggested actions') }}
            </div>
            <div class="flex flex-col gap-2">
              <Button
                v-for="(s, i) in overview.suggestions || []"
                :key="i"
                :label="s.label"
                :loading="acting === i"
                @click="runSuggestion(s, i)"
              />
            </div>
          </div>

          <div v-if="overview.draft">
            <div class="mb-2 flex items-center justify-between">
              <div class="text-p-sm-medium text-ink-gray-7">
                {{ __('Follow-up draft') }}
              </div>
              <Button
                size="sm"
                variant="ghost"
                :label="__('Copy')"
                @click="copyDraft"
              />
            </div>
            <div class="rounded-lg border border-outline-gray-modals p-3 text-p-sm">
              <div class="text-ink-gray-5">{{ __('Subject') }}</div>
              <div class="mb-2 font-medium">{{ overview.draft.subject }}</div>
              <div class="whitespace-pre-wrap text-ink-gray-8">
                {{ overview.draft.body }}
              </div>
              <div class="mt-3 border-t border-outline-gray-modals pt-2">
                <div class="text-ink-gray-5">{{ __('SMS') }}</div>
                <div class="text-ink-gray-8">{{ overview.draft.sms }}</div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </template>
    <template #actions>
      <Button :label="__('Close')" @click="open = false" />
      <Button variant="solid" :label="__('Refresh')" :loading="loading" @click="load" />
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  Button,
  Dialog,
  LoadingIndicator,
  call,
  toast,
} from 'frappe-ui'
import { copyToClipboard } from '@/utils'

const props = defineProps({
  deal: { type: String, required: true },
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'done'])

const open = ref(props.modelValue)
const loading = ref(false)
const acting = ref(null)
const overview = ref(null)

watch(
  () => props.modelValue,
  (v) => {
    open.value = v
    if (v) load()
  },
)
watch(open, (v) => emit('update:modelValue', v))

async function load() {
  loading.value = true
  try {
    overview.value = await call('crm.life.api.assistant_overview', {
      deal: props.deal,
    })
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Could not load assistant'))
  } finally {
    loading.value = false
  }
}

async function runSuggestion(s, i) {
  if (s.type === 'draft') {
    overview.value = {
      ...overview.value,
      draft: overview.value.draft,
    }
    toast.success(__('Draft ready below'))
    return
  }
  if (s.type === 'open_tab') {
    emit('done', { openTab: s.tab })
    open.value = false
    return
  }
  acting.value = i
  try {
    await call('crm.life.api.assistant_apply', {
      deal: props.deal,
      suggestion: s,
    })
    toast.success(__('Done'))
    emit('done', s)
    await load()
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Action failed'))
  } finally {
    acting.value = null
  }
}

function copyDraft() {
  const d = overview.value?.draft
  if (!d) return
  copyToClipboard(`${d.subject}\n\n${d.body}`)
  toast.success(__('Copied'))
}
</script>
