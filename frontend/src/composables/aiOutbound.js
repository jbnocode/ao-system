import { call, toast } from 'frappe-ui'
import { ref } from 'vue'

export const aiCallReady = ref(false)
export const aiCallBusy = ref(false)

let loadPromise = null

/** Load whether the current user can place AI outbound calls (GPT-Live + Twilio). */
export function loadAiCallReady(force = false) {
  if (loadPromise && !force) return loadPromise
  loadPromise = call('crm.live.api.get_my_assignment')
    .then((data) => {
      aiCallReady.value = Boolean(
        data?.enabled &&
          data?.has_openai_key &&
          data?.assignment?.phone_number,
      )
      return aiCallReady.value
    })
    .catch(() => {
      aiCallReady.value = false
      return false
    })
  return loadPromise
}

/**
 * Start a GPT-Live outbound call for the given number / CRM record.
 * @returns {Promise<object|null>}
 */
export async function startAiOutboundCall({
  toNumber,
  referenceDoctype = null,
  referenceDocname = null,
  quiet = false,
} = {}) {
  const phone = (toNumber || '').replace(/\s/g, '')
  if (!phone) {
    if (!quiet) toast.error(__('Please set a mobile number to make calls'))
    return null
  }

  await loadAiCallReady()
  if (!aiCallReady.value) {
    if (!quiet) {
      toast.error(
        __(
          'AI Caller is not ready. Ask a manager to assign a Twilio number, or check AI Agent.',
        ),
      )
    }
    return null
  }

  if (aiCallBusy.value) return null
  aiCallBusy.value = true
  try {
    const payload = { to_number: phone }
    if (referenceDoctype && referenceDocname) {
      payload.reference_doctype = referenceDoctype
      payload.reference_docname = referenceDocname
    }
    const data = await call('crm.live.api.start_outbound_call', payload)
    if (!quiet) toast.success(__('AI call started'))
    return data
  } catch (e) {
    if (!quiet) {
      toast.error(
        e?.messages?.[0] || e?.message || __('Could not start AI call'),
      )
    }
    throw e
  } finally {
    aiCallBusy.value = false
  }
}
