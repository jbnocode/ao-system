import { computed, ref } from 'vue'

const STORAGE_KEY = 'crm-ai-sessions'

export const showAiSidebar = ref(false)

export function openAiSidebar() {
  showAiSidebar.value = true
}

export function closeAiSidebar() {
  showAiSidebar.value = false
}

export function toggleAiSidebar() {
  showAiSidebar.value = !showAiSidebar.value
}

export const aiSessions = ref(loadSessions())
export const activeSessionId = ref(aiSessions.value[0]?.id || null)
export const chatSearchQuery = ref('')

export const activeSession = computed(
  () => aiSessions.value.find((s) => s.id === activeSessionId.value) || null,
)

export const filteredSessions = computed(() => {
  const q = chatSearchQuery.value.trim().toLowerCase()
  if (!q) return aiSessions.value
  return aiSessions.value.filter((s) => s.title.toLowerCase().includes(q))
})

export const sessionGroups = computed(() =>
  groupSessions(filteredSessions.value),
)

export function newChatSession() {
  const session = makeSession()
  aiSessions.value = [session, ...aiSessions.value]
  activeSessionId.value = session.id
  persist()
  return session
}

export function selectChatSession(id) {
  if (!aiSessions.value.some((s) => s.id === id)) return
  activeSessionId.value = id
}

export function clearActiveChat() {
  const session = activeSession.value
  if (!session) {
    newChatSession()
    return
  }
  session.messages = []
  session.title = __('New chat')
  session.updatedAt = Date.now()
  touchSessions()
}

export function deleteChatSession(id) {
  if (!id) return
  const wasActive = activeSessionId.value === id
  aiSessions.value = aiSessions.value.filter((s) => s.id !== id)
  if (!aiSessions.value.length) {
    newChatSession()
    return
  }
  if (wasActive || !aiSessions.value.some((s) => s.id === activeSessionId.value)) {
    activeSessionId.value = aiSessions.value[0].id
  }
  persist()
}

export function deleteActiveChat() {
  deleteChatSession(activeSessionId.value)
}

export function getSessionShareText(id) {
  const session = aiSessions.value.find((s) => s.id === id)
  if (!session) return ''
  const lines = [`# ${session.title || __('New chat')}`, '']
  for (const msg of session.messages || []) {
    const role = msg.role === 'user' ? __('You') : __('AI')
    lines.push(`${role}: ${msg.content || ''}`)
    lines.push('')
  }
  return lines.join('\n').trim()
}

export function setSessionMessages(messages) {
  let session = activeSession.value
  if (!session) {
    session = newChatSession()
  }
  session.messages = messages
  session.updatedAt = Date.now()
  const firstUser = messages.find((m) => m.role === 'user')
  if (firstUser?.content) {
    session.title = titleFrom(firstUser.content)
  } else if (!messages.length) {
    session.title = __('New chat')
  }
  aiSessions.value = [
    session,
    ...aiSessions.value.filter((s) => s.id !== session.id),
  ]
  persist()
}

function makeSession() {
  return {
    id: `chat_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    title: __('New chat'),
    messages: [],
    updatedAt: Date.now(),
  }
}

function titleFrom(text) {
  const t = String(text || '')
    .trim()
    .replace(/\s+/g, ' ')
  if (!t) return __('New chat')
  return t.length > 48 ? `${t.slice(0, 48)}…` : t
}

function touchSessions() {
  aiSessions.value = [...aiSessions.value]
  persist()
}

function loadSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return [makeSession()]
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || !parsed.length) return [makeSession()]
    return parsed.map((s) => ({
      id: s.id,
      title: s.title || __('New chat'),
      messages: Array.isArray(s.messages) ? s.messages : [],
      updatedAt: s.updatedAt || Date.now(),
    }))
  } catch {
    return [makeSession()]
  }
}

function persist() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(
        aiSessions.value.map(({ id, title, messages, updatedAt }) => ({
          id,
          title,
          messages,
          updatedAt,
        })),
      ),
    )
  } catch {
    /* ignore quota */
  }
}

function groupSessions(sessions) {
  const now = new Date()
  const startOfToday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate(),
  )
  const startOfYesterday = new Date(startOfToday)
  startOfYesterday.setDate(startOfYesterday.getDate() - 1)
  const startOfWeek = new Date(startOfToday)
  startOfWeek.setDate(startOfWeek.getDate() - 7)

  const groups = [
    { key: 'today', label: __('Today'), items: [] },
    { key: 'yesterday', label: __('Yesterday'), items: [] },
    { key: 'week', label: __('Previous 7 days'), items: [] },
    { key: 'older', label: __('Older'), items: [] },
  ]

  for (const s of sessions) {
    const d = new Date(s.updatedAt)
    if (d >= startOfToday) groups[0].items.push(s)
    else if (d >= startOfYesterday) groups[1].items.push(s)
    else if (d >= startOfWeek) groups[2].items.push(s)
    else groups[3].items.push(s)
  }

  return groups.filter((g) => g.items.length)
}

if (!activeSessionId.value && aiSessions.value.length) {
  activeSessionId.value = aiSessions.value[0].id
}
