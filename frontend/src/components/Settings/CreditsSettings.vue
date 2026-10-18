<template>
  <div class="flex h-full flex-col overflow-y-auto p-8 text-ink-gray-8">
    <h2 class="mb-1 text-2xl-semibold">{{ __('Credits') }}</h2>
    <p class="mb-6 text-p-base text-ink-gray-6">
      {{
        __(
          'Top up the team pool, then disburse credits to agents. Agents spend from their own balance.',
        )
      }}
    </p>

    <div v-if="loading" class="flex justify-center py-12">
      <LoadingIndicator class="w-4" />
    </div>
    <template v-else>
      <div
        class="mb-8 max-w-2xl rounded-lg border border-outline-gray-modals bg-surface-white p-4"
      >
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div class="text-p-base-medium text-ink-gray-8">
              {{ __('Team credit pool') }}
            </div>
            <div class="mt-1 text-p-sm text-ink-gray-5">
              {{ __('Add credits here before disbursing to agents.') }}
            </div>
          </div>
          <Badge
            :label="__('Balance: {0}', [teamBalance])"
            theme="blue"
            variant="subtle"
          />
        </div>
        <div class="mt-4 flex flex-wrap items-end gap-3">
          <FormControl
            v-model="topUpAmount"
            :label="__('Top up amount')"
            type="number"
            class="w-36"
          />
          <Button
            variant="solid"
            :label="__('Top up')"
            :loading="toppingUp"
            :disabled="!Number(topUpAmount)"
            @click="topUp"
          />
        </div>
      </div>

      <h3 class="mb-1 text-lg-semibold">{{ __('Disburse to agents') }}</h3>
      <p class="mb-4 text-p-sm text-ink-gray-5 max-w-2xl">
        {{ __('Move credits from the team pool into an agent balance.') }}
      </p>

      <div v-if="agentsLoading" class="flex justify-center py-8 max-w-2xl">
        <LoadingIndicator class="w-4" />
      </div>
      <div v-else class="mb-10 max-w-2xl flex flex-col">
        <div
          v-for="row in agents"
          :key="row.user"
          class="flex flex-col gap-3 border-b border-outline-gray-modals py-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-p-base-medium text-ink-gray-8 truncate">
                {{ row.user_name }}
              </span>
              <Badge
                :label="__('Balance: {0}', [row.credits])"
                variant="subtle"
                theme="gray"
              />
            </div>
            <button
              type="button"
              class="mt-0.5 text-p-sm text-ink-gray-5 hover:text-ink-gray-8 underline-offset-2 hover:underline"
              @click="openUsage(row.user)"
            >
              {{ __('Check usage') }}
            </button>
          </div>
          <div class="flex flex-wrap items-end gap-2">
            <FormControl
              v-model="disburseDraft[row.user]"
              :label="__('Amount')"
              type="number"
              class="w-28"
            />
            <Button
              variant="subtle"
              :label="__('Disburse')"
              :loading="disbursing === row.user"
              :disabled="!Number(disburseDraft[row.user])"
              @click="disburse(row.user)"
            />
          </div>
        </div>
        <div v-if="!agents.length" class="text-p-sm text-ink-gray-5 py-4">
          {{
            __(
              'No CRM users found. Invite users with Sales User or Sales Manager roles first.',
            )
          }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import {
  activeSettingsPage,
  creditUsageUserFilter,
} from '@/composables/settings'
import {
  Badge,
  Button,
  FormControl,
  LoadingIndicator,
  call,
  toast,
} from 'frappe-ui'
import { onMounted, reactive, ref } from 'vue'

const loading = ref(true)
const agentsLoading = ref(false)
const toppingUp = ref(false)
const disbursing = ref('')
const teamBalance = ref(0)
const topUpAmount = ref(500)
const agents = ref([])
const disburseDraft = reactive({})

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadWallet(), loadAgents()])
  } finally {
    loading.value = false
  }
})

async function loadWallet() {
  try {
    const res = await call('crm.ai.credits.get_team_wallet')
    teamBalance.value = res?.balance ?? 0
  } catch (e) {
    toast.error(
      e?.messages?.join?.(' ') || e?.message || __('Could not load team wallet'),
    )
  }
}

async function loadAgents() {
  agentsLoading.value = true
  try {
    const rows = await call('crm.ai.credits.list_agent_credits')
    agents.value = rows || []
    for (const row of agents.value) {
      if (disburseDraft[row.user] == null) disburseDraft[row.user] = 50
    }
  } catch (e) {
    toast.error(
      e?.messages?.join?.(' ') || e?.message || __('Could not load agents'),
    )
  } finally {
    agentsLoading.value = false
  }
}

async function topUp() {
  toppingUp.value = true
  try {
    const res = await call('crm.ai.credits.top_up_team_credits', {
      amount: Number(topUpAmount.value) || 0,
    })
    teamBalance.value = res?.balance ?? teamBalance.value
    toast.success(__('Team pool updated. Balance: {0}', [teamBalance.value]))
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Top up failed'))
  } finally {
    toppingUp.value = false
  }
}

async function disburse(user) {
  disbursing.value = user
  try {
    const res = await call('crm.ai.credits.disburse_credits', {
      user,
      amount: Number(disburseDraft[user]) || 0,
    })
    teamBalance.value = res?.team_balance ?? teamBalance.value
    const row = agents.value.find((a) => a.user === user)
    if (row) row.credits = res.credits
    toast.success(__('Disbursed. Agent balance: {0}', [res.credits]))
  } catch (e) {
    toast.error(e?.messages?.join?.(' ') || e?.message || __('Disburse failed'))
  } finally {
    disbursing.value = ''
  }
}

function openUsage(user) {
  creditUsageUserFilter.value = user || ''
  activeSettingsPage.value = 'Usage'
}
</script>
