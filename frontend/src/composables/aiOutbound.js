import { call, toast } from 'frappe-ui'
import { ref } from 'vue'

export const aiCallReady = ref(false)
export const aiCallBusy = ref(false)

let loadPromise = null

/** Load whether the current user can place AI outbound calls. */
export function loadAiCallReady(force = false) {
  if (loadPromise && !force) return loadPromise
  loadPromise = call('crm.vapi.api.get_my_assignment')
    .then((data) => {
      // Ready when Vapi is on and a number+assistant are assigned.
      // Voice/script/compliance live under AI Agent (no onboarding gate).
      aiCallReady.value = Boolean(
        data?.enabled &&
          data?.has_private_key &&
          data?.assignment?.phone_number &&
          data?.assignment?.vapi_assistant_id &&
          data?.assignment?.vapi_phone_id,
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
 * Start a Vapi outbound call for the given number / CRM record.
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
          'AI Caller is not ready. Ask a manager to link a number, or check AI Agent.',
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
    const data = await call('crm.vapi.api.start_outbound_call', payload)
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
