<template>
  <div class="rounded-5 border border-outline-gray-modals bg-surface-gray-1 p-4">
    <div class="mb-3 flex items-start justify-between gap-2">
      <div>
        <div class="text-p-base-medium text-ink-gray-8">
          {{ __('Test your AI agent') }}
        </div>
        <p class="text-p-sm text-ink-gray-5">
          {{
            __(
              'Talk to GPT-Live in the browser before placing outbound phone calls.',
            )
          }}
        </p>
      </div>
      <Badge
        v-if="statusLabel"
        :label="statusLabel"
        :theme="statusTheme"
        variant="subtle"
      />
    </div>

    <div v-if="hint" class="mb-3 text-p-sm text-ink-gray-5">
      {{ hint }}
    </div>
    <ErrorMessage v-if="error" class="mb-3" :message="error" />

    <div class="flex flex-wrap gap-2">
      <Button
        v-if="!active"
        variant="solid"
        :label="__('Start test call')"
        :loading="connecting"
        :disabled="!ready"
        @click="start"
      />
      <Button
        v-else
        variant="subtle"
        theme="red"
        :label="__('End test')"
        @click="stop"
      />
    </div>
  </div>
</template>

<script setup>
import {
  Badge,
  Button,
  ErrorMessage,
  call,
} from 'frappe-ui'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const ready = ref(false)
const hint = ref('')
const error = ref('')
const connecting = ref(false)
const active = ref(false)
const status = ref('idle')

let pc = null
let localStream = null
let remoteAudio = null

const statusLabel = computed(() => {
  if (status.value === 'connecting') return __('Connecting')
  if (status.value === 'live') return __('Live')
  if (status.value === 'ended') return __('Ended')
  return ''
})

const statusTheme = computed(() => {
  if (status.value === 'live') return 'green'
  if (status.value === 'connecting') return 'orange'
  return 'gray'
})

onMounted(load)
onBeforeUnmount(stop)

async function load() {
  try {
    const cfg = await call('crm.live.api.get_widget_config')
    if (!cfg.enabled) {
      hint.value = __(
        'AI Live is disabled. Ask an admin to enable it in Settings → AI Live.',
      )
      return
    }
    if (!cfg.has_openai_key) {
      hint.value = __(
        'OpenAI Live key is missing. Ask a System Manager to save it under Settings → AI Live.',
      )
      return
    }
    ready.value = true
    hint.value = cfg.phone_number
      ? __('Assigned number: {0}', [cfg.phone_number])
      : __(
          'No phone number yet — you can still test the voice agent in-browser.',
        )
  } catch (e) {
    hint.value =
      e?.messages?.[0] || e?.message || __('Could not load Live test widget')
  }
}

async function start() {
  if (connecting.value || active.value) return
  connecting.value = true
  error.value = ''
  status.value = 'connecting'
  try {
    localStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    })

    remoteAudio = new Audio()
    remoteAudio.autoplay = true
    pc.ontrack = (ev) => {
      remoteAudio.srcObject = ev.streams[0]
    }

    for (const track of localStream.getTracks()) {
      pc.addTrack(track, localStream)
    }

    const offer = await pc.createOffer({ offerToReceiveAudio: true })
    await pc.setLocalDescription(offer)
    await waitForIce(pc)

    const result = await call('crm.live.api.create_webrtc_session', {
      sdp: pc.localDescription.sdp,
    })
    const answerSdp =
      result?.transport?.sdp ||
      result?.sdp ||
      result?.session?.transport?.sdp
    if (!answerSdp) {
      throw new Error(__('Live session did not return an SDP answer'))
    }
    await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp })
    active.value = true
    status.value = 'live'
  } catch (e) {
    error.value =
      e?.messages?.[0] || e?.message || __('Could not start Live test call')
    status.value = 'ended'
    stop()
  } finally {
    connecting.value = false
  }
}

function waitForIce(peer, timeoutMs = 2500) {
  if (peer.iceGatheringState === 'complete') return Promise.resolve()
  return new Promise((resolve) => {
    const t = setTimeout(() => resolve(), timeoutMs)
    peer.addEventListener('icegatheringstatechange', () => {
      if (peer.iceGatheringState === 'complete') {
        clearTimeout(t)
        resolve()
      }
    })
  })
}

function stop() {
  active.value = false
  if (status.value === 'live' || status.value === 'connecting') {
    status.value = 'ended'
  }
  try {
    pc?.getSenders()?.forEach((s) => s.track?.stop())
    pc?.close()
  } catch {
    /* ignore */
  }
  pc = null
  try {
    localStream?.getTracks()?.forEach((t) => t.stop())
  } catch {
    /* ignore */
  }
  localStream = null
  if (remoteAudio) {
    remoteAudio.srcObject = null
    remoteAudio = null
  }
}
</script>
