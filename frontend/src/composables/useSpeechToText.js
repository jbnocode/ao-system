import { toast } from 'frappe-ui'
import { onBeforeUnmount, ref } from 'vue'

/**
 * Browser SpeechRecognition → append transcribed text to a draft ref.
 */
export function useSpeechToText(draftRef) {
  const listening = ref(false)
  const supported = ref(false)
  let recognition = null

  const SpeechRecognition =
    typeof window !== 'undefined'
      ? window.SpeechRecognition || window.webkitSpeechRecognition
      : null

  supported.value = Boolean(SpeechRecognition)

  function ensureRecognition() {
    if (!SpeechRecognition) return null
    if (recognition) return recognition

    recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = true
    recognition.lang =
      (typeof navigator !== 'undefined' && navigator.language) || 'en-US'

    recognition.onresult = (event) => {
      let interim = ''
      let final = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0]?.transcript || ''
        if (event.results[i].isFinal) final += piece
        else interim += piece
      }
      const text = (final || interim).trim()
      if (!text || !draftRef) return
      if (final) {
        const cur = (draftRef.value || '').trim()
        draftRef.value = cur ? `${cur} ${final.trim()}` : final.trim()
      }
    }

    recognition.onerror = (event) => {
      listening.value = false
      const err = event?.error
      if (err === 'not-allowed' || err === 'service-not-allowed') {
        toast.error(__('Microphone permission denied'))
      } else if (err !== 'aborted' && err !== 'no-speech') {
        toast.error(__('Speech recognition failed'))
      }
    }

    recognition.onend = () => {
      listening.value = false
    }

    return recognition
  }

  function start() {
    const rec = ensureRecognition()
    if (!rec) {
      toast.error(__('Speech to text is not supported in this browser'))
      return
    }
    try {
      listening.value = true
      rec.start()
    } catch {
      listening.value = false
      toast.error(__('Could not start listening'))
    }
  }

  function stop() {
    try {
      recognition?.stop()
    } catch {
      /* ignore */
    }
    listening.value = false
  }

  function toggle() {
    if (listening.value) stop()
    else start()
  }

  onBeforeUnmount(() => {
    stop()
    recognition = null
  })

  return { listening, supported, start, stop, toggle }
}
