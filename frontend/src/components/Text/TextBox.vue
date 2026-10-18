<template>
  <div class="flex items-end gap-2 px-3 py-2.5 sm:px-4" v-bind="$attrs">
    <Textarea
      ref="textareaRef"
      v-model="content"
      type="textarea"
      class="min-h-8 w-full"
      :rows="rows"
      :disabled="disabled"
      :placeholder="
        disabled
          ? __('SMS is not available. Assign a phone number in Telephony.')
          : __('Type your message here...')
      "
      @focus="rows = 4"
      @blur="rows = 1"
      @keydown.enter.stop="(e) => sendTextMessage(e)"
    />
    <Button
      variant="solid"
      :disabled="disabled || !content.trim() || sending"
      :loading="sending"
      :label="__('Send')"
      @click="send()"
    />
  </div>
</template>

<script setup>
import { Button, Textarea, call, toast } from 'frappe-ui'
import { nextTick, ref } from 'vue'

const props = defineProps({
  phone: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['sent'])

const rows = ref(1)
const textareaRef = ref(null)
const content = ref('')
const sending = ref(false)

function show() {
  nextTick(() => textareaRef.value?.el?.focus())
}

function sendTextMessage(event) {
  if (event.shiftKey) return
  event.preventDefault()
  send()
}

async function send() {
  const message = content.value.trim()
  if (!message || !props.phone || props.disabled || sending.value) return
  sending.value = true
  content.value = ''
  try {
    await call('crm.api.sms.send_sms', {
      to: props.phone,
      message,
    })
    emit('sent')
  } catch (error) {
    content.value = message
    toast.error(error.messages?.[0] || __('Failed to send SMS'))
  } finally {
    sending.value = false
    textareaRef.value?.el?.blur()
  }
}

defineExpose({ show })
</script>
