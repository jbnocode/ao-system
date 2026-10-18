<template>
  <div
    v-if="ready"
    class="rounded-5 border border-outline-gray-modals bg-surface-gray-1 p-4"
  >
    <div class="mb-2 flex items-center justify-between gap-2">
      <div>
        <div class="text-p-base-medium text-ink-gray-8">
          {{ __('Test your AI agent') }}
        </div>
        <p class="text-p-sm text-ink-gray-5">
          {{
            __(
              'Talk to your AI agent in the browser before making outbound calls.',
            )
          }}
        </p>
      </div>
    </div>
    <div ref="host" class="min-h-[52px]" />
  </div>
  <div
    v-else-if="hint"
    class="rounded-5 border border-outline-gray-modals px-4 py-3 text-p-sm text-ink-gray-5"
  >
    {{ hint }}
  </div>
</template>

<script setup>
import { call } from 'frappe-ui'
import { onBeforeUnmount, onMounted, ref } from 'vue'

const host = ref(null)
const ready = ref(false)
const hint = ref('')
let scriptEl = null

onMounted(load)
onBeforeUnmount(cleanup)

async function load() {
  try {
    const cfg = await call('crm.vapi.api.get_widget_config')
    if (!cfg.enabled) {
      hint.value = __(
        'AI Caller is disabled. Ask an admin to enable it in Settings.',
      )
      return
    }
    if (!cfg.public_key) {
      hint.value = __(
        'AI Caller is not fully configured. Ask an admin to finish setup in Settings.',
      )
      return
    }
    if (!cfg.assistant_id) {
      hint.value = __(
        'No AI agent yet. Ask your admin to link a phone number under Settings → AI Caller.',
      )
      return
    }
    ready.value = true
    await ensureScript()
    mountWidget(cfg.public_key, cfg.assistant_id)
  } catch (e) {
    hint.value = e?.messages?.[0] || e?.message || __('Could not load test widget')
  }
}

function ensureScript() {
  return new Promise((resolve, reject) => {
    if (customElements.get('vapi-widget')) {
      resolve()
      return
    }
    const existing = document.querySelector('script[data-vapi-widget]')
    if (existing) {
      existing.addEventListener('load', () => resolve())
      existing.addEventListener('error', () => reject(new Error('Widget script failed')))
      return
    }
    scriptEl = document.createElement('script')
    scriptEl.src =
      'https://unpkg.com/@vapi-ai/client-sdk-react/dist/embed/widget.umd.js'
    scriptEl.async = true
    scriptEl.dataset.vapiWidget = '1'
    scriptEl.onload = () => resolve()
    scriptEl.onerror = () => reject(new Error('Widget script failed'))
    document.head.appendChild(scriptEl)
  })
}

function mountWidget(publicKey, assistantId) {
  if (!host.value) return
  host.value.innerHTML = ''
  const el = document.createElement('vapi-widget')
  el.setAttribute('public-key', publicKey)
  el.setAttribute('assistant-id', assistantId)
  el.setAttribute('mode', 'voice')
  el.setAttribute('theme', 'light')
  el.setAttribute('size', 'compact')
  el.setAttribute('position', 'bottom-right')
  host.value.appendChild(el)
}

function cleanup() {
  if (host.value) host.value.innerHTML = ''
}
</script>
