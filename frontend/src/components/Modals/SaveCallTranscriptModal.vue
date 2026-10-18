<template>
  <Dialog
    v-model="show"
    :options="{
      title: hasExisting ? __('Edit transcript') : __('Save transcript'),
      size: 'xl',
    }"
  >
    <template #body-content>
      <div class="space-y-4">
        <p class="text-p-sm text-ink-gray-6">
          {{
            __(
              'Paste or type the call transcript. It is saved on the call log and as a note on the linked lead or deal when available.',
            )
          }}
        </p>
        <FormControl
          v-model="form.summary"
          type="textarea"
          :label="__('Summary (optional)')"
          :rows="3"
        />
        <FormControl
          v-model="form.transcript"
          type="textarea"
          :label="__('Transcript')"
          :rows="10"
        />
        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <Button variant="subtle" :label="__('Cancel')" @click="show = false" />
      <Button
        variant="solid"
        :label="__('Save')"
        :loading="saving"
        :disabled="!form.transcript?.trim()"
        @click="save"
      />
    </template>
  </Dialog>
</template>

<script setup>
import {
  Button,
  Dialog,
  ErrorMessage,
  FormControl,
  call,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  callLogName: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const saving = ref(false)
const loading = ref(false)
const error = ref('')
const hasExisting = ref(false)
const form = reactive({
  summary: '',
  transcript: '',
})

watch(
  () => [props.modelValue, props.callLogName],
  async ([open, name]) => {
    if (!open || !name) return
    error.value = ''
    form.summary = ''
    form.transcript = ''
    hasExisting.value = false
    loading.value = true
    try {
      const doc = await call('frappe.client.get_value', {
        doctype: 'CRM Call Log',
        filters: name,
        fieldname: ['ai_summary', 'ai_transcript'],
      })
      form.summary = doc?.ai_summary || ''
      form.transcript = doc?.ai_transcript || ''
      hasExisting.value = Boolean(form.transcript)
    } catch (e) {
      error.value = e?.messages?.join?.('\n') || e?.message || __('Could not load call log')
    } finally {
      loading.value = false
    }
  },
)

async function save() {
  const transcript = (form.transcript || '').trim()
  if (!transcript || !props.callLogName) return
  saving.value = true
  error.value = ''
  try {
    await call('crm.fcrm.doctype.crm_call_log.crm_call_log.save_transcript', {
      name: props.callLogName,
      transcript,
      summary: (form.summary || '').trim(),
    })
    toast.success(__('Transcript saved'))
    show.value = false
    emit('saved')
  } catch (e) {
    error.value =
      e?.messages?.join?.('\n') || e?.message || __('Could not save transcript')
  } finally {
    saving.value = false
  }
}
</script>
