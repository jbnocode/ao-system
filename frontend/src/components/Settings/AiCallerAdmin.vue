<template>
  <div class="flex h-full flex-col overflow-y-auto p-8 text-ink-gray-8">
    <div class="mb-6 flex items-start justify-between gap-3">
      <div>
        <h2 class="mb-1 text-2xl-semibold">{{ __('AI Caller') }}</h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Link phone numbers to agents for AI outbound. Buy numbers under Telephony → Phone Numbers. Agents finish voice, script, and compliance in AI Call setup.',
            )
          }}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <Button
          variant="subtle"
          :label="__('Usage dashboard')"
          @click="openUsage"
        />
        <Button
          variant="subtle"
          icon-left="lucide-refresh-cw"
          :label="__('Refresh')"
          :loading="numbers.loading || assignments.loading"
          @click="reload"
        />
      </div>
    </div>

    <div class="mb-8 max-w-2xl rounded-5 border border-outline-gray-modals bg-surface-gray-1 p-4">
      <div class="mb-3 text-p-base-medium text-ink-gray-8">
        {{ __('Link number to agent') }}
      </div>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div class="min-w-0 flex-1">
          <label class="mb-1.5 block text-xs text-ink-gray-5">{{
            __('Phone number')
          }}</label>
          <FormControl
            v-model="linkForm.phone_number"
            type="select"
            :options="numberOptions"
          />
        </div>
        <div class="min-w-0 flex-1">
          <label class="mb-1.5 block text-xs text-ink-gray-5">{{
            __('Assign to')
          }}</label>
          <Link
            :model-value="linkForm.user"
            doctype="User"
            @update:model-value="linkForm.user = $event"
          />
        </div>
        <Button
          variant="solid"
          :label="__('Link & assign')"
          :loading="linking"
          :disabled="!linkForm.phone_number || !linkForm.user"
          @click="linkAssign"
        />
      </div>
      <ErrorMessage v-if="linkError" class="mt-2" :message="linkError" />
      <p class="mt-2 text-p-sm text-ink-gray-5">
        {{
          __(
            'Links the number for AI calling, creates an agent, and assigns it to the user.',
          )
        }}
      </p>
    </div>

    <div class="mb-2 text-p-base-medium text-ink-gray-8">
      {{ __('Assignments') }}
    </div>
    <div
      v-if="assignments.loading && !assignments.data?.length"
      class="flex justify-center py-10"
    >
      <LoadingIndicator class="w-4" />
    </div>
    <div
      v-else-if="!assignments.data?.length"
      class="rounded-5 border border-outline-gray-modals px-4 py-8 text-center text-p-sm text-ink-gray-5"
    >
      {{ __('No AI caller agents yet.') }}
    </div>
    <div v-else class="flex flex-col">
      <div
        v-for="row in assignments.data"
        :key="row.name"
        class="flex flex-col gap-2 border-b border-outline-gray-modals py-3 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="min-w-0">
          <div class="text-p-base-medium text-ink-gray-8">
            {{ row.user_name || row.user }}
          </div>
          <div class="text-p-sm text-ink-gray-5">
            {{ row.phone_number || __('No number') }}
            <span v-if="row.setup_completed"> · {{ __('Setup done') }}</span>
            <span v-else> · {{ __('Setup pending') }}</span>
          </div>
        </div>
        <Button
          size="sm"
          variant="subtle"
          :label="__('Unassign')"
          :loading="unassigning === row.user"
          @click="unassign(row.user)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import Link from '@/components/Controls/Link.vue'
import { showSettings } from '@/composables/settings'
import {
  Button,
  ErrorMessage,
  FormControl,
  LoadingIndicator,
  call,
  createResource,
  toast,
} from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const linking = ref(false)
const linkError = ref('')
const unassigning = ref('')
const linkForm = reactive({ phone_number: '', user: '' })

const numbers = createResource({
  url: 'crm.vapi.api.list_twilio_numbers_for_link',
  auto: true,
  onError: (err) => {
    err?.messages?.forEach((msg) => toast.error(msg))
  },
})

const assignments = createResource({
  url: 'crm.vapi.api.list_assignments',
  auto: true,
  onError: (err) => {
    err?.messages?.forEach((msg) => toast.error(msg))
  },
})

const numberOptions = computed(() => {
  const rows = numbers.data || []
  return [
    { label: __('Select a number'), value: '' },
    ...rows.map((n) => ({
      label: n.ai_linked
        ? `${n.phone_number} (${__('linked')} → ${n.ai_user_name || n.ai_user})`
        : n.phone_number,
      value: n.phone_number,
    })),
  ]
})

function reload() {
  numbers.reload()
  assignments.reload()
}

function openUsage() {
  showSettings.value = false
  router.push({ name: 'AI Caller Usage' })
}

async function linkAssign() {
  if (!linkForm.phone_number || !linkForm.user) return
  linking.value = true
  linkError.value = ''
  try {
    await call('crm.vapi.api.link_and_assign', {
      phone_number: linkForm.phone_number,
      user: linkForm.user,
    })
    toast.success(__('Number linked and assigned'))
    linkForm.phone_number = ''
    linkForm.user = ''
    reload()
  } catch (err) {
    linkError.value =
      err?.messages?.join('\n') || err?.message || __('Could not link number')
  } finally {
    linking.value = false
  }
}

async function unassign(user) {
  unassigning.value = user
  try {
    await call('crm.vapi.api.unassign_agent', { user })
    toast.success(__('Unassigned'))
    reload()
  } catch (err) {
    err?.messages?.forEach((msg) => toast.error(msg))
  } finally {
    unassigning.value = ''
  }
}
</script>
