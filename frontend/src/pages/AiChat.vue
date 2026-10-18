<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <LayoutHeader>
      <template #left-header>
        <Breadcrumbs :items="breadcrumbs" />
      </template>
      <template #right-header>
        <Button
          :label="__('History')"
          variant="subtle"
          icon-left="lucide-history"
          :aria-pressed="historyOpen"
          @click="historyOpen = !historyOpen"
        />
      </template>
    </LayoutHeader>

    <div class="flex min-h-0 flex-1 overflow-hidden bg-surface-white">
      <div
        class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden transition-[flex-basis] duration-300 ease-in-out"
      >
        <AiHome
          v-if="view === 'home'"
          :briefing="briefing"
          :loading="asking"
          @ask="startAsk"
        />
        <AiChatThread
          v-else
          ref="threadRef"
          class="min-h-0 flex-1"
          show-chrome
          context-type="home"
          :snapshot="briefingSnapshot"
          :initial-prompt="pendingPrompt"
          :empty-hint="
            __('Ask about your tasks, leads, meetings, or CRM workflows.')
          "
          :placeholder="__('Ask anything about your CRM…')"
          @new-chat="goHome"
        />
      </div>

      <div
        class="h-full shrink-0 overflow-hidden transition-[width] duration-300 ease-in-out"
        :class="historyOpen ? 'w-60' : 'w-0'"
        :aria-hidden="!historyOpen"
      >
        <AiChatHistory
          side="right"
          class="h-full w-60 transition-transform duration-300 ease-in-out will-change-transform"
          :class="historyOpen ? 'translate-x-0' : 'translate-x-full'"
          @new-chat="onHistoryNewChat"
          @select="onHistorySelect"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import AiChatHistory from '@/components/AI/AiChatHistory.vue'
import AiChatThread from '@/components/AI/AiChatThread.vue'
import AiHome from '@/components/AI/AiHome.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import { newChatSession } from '@/composables/aiChat'
import { Breadcrumbs, Button, createResource, toast } from 'frappe-ui'
import { computed, nextTick, ref } from 'vue'

const breadcrumbs = [{ label: __('AI'), route: { name: 'AI' } }]
const view = ref('home')
const asking = ref(false)
const pendingPrompt = ref('')
const threadRef = ref(null)
const historyOpen = ref(false)

const homeBriefing = createResource({
  url: 'crm.ai.home.get_home_briefing',
  auto: true,
  onError(e) {
    toast.error(
      e?.messages?.join?.(' ') || e?.message || __('Could not load AI home'),
    )
  },
})

const briefing = computed(() => homeBriefing.data || null)

function briefingSnapshot() {
  if (!briefing.value) return null
  return {
    stats: briefing.value.stats,
    tasks: briefing.value.tasks,
    meetings: briefing.value.meetings,
    suggestions: briefing.value.suggestions,
  }
}

async function startAsk(prompt) {
  const text = (prompt || '').trim()
  if (!text || asking.value) return
  asking.value = true
  try {
    newChatSession()
    view.value = 'chat'
    await nextTick()
    if (threadRef.value?.sendPrompt) {
      await threadRef.value.sendPrompt(text)
    } else {
      pendingPrompt.value = text
      await nextTick()
      pendingPrompt.value = ''
    }
  } finally {
    asking.value = false
  }
}

function goHome() {
  view.value = 'home'
  pendingPrompt.value = ''
  homeBriefing.reload()
}

function onHistoryNewChat() {
  goHome()
}

function onHistorySelect() {
  view.value = 'chat'
}
</script>
