import { computed, ref } from 'vue'

const STORAGE_KEY = 'crm-ai-caller-setup'

/** Built-in GPT-Live voices (OpenAI). */
export const AI_CALLER_VOICES = [
  {
    id: 'cedar',
    label: 'Cedar',
    description: 'Natural and conversational — default for Live.',
  },
  {
    id: 'marin',
    label: 'Marin',
    description: 'Professional and clear.',
  },
  {
    id: 'alloy',
    label: 'Alloy',
    description: 'Neutral and balanced.',
  },
  {
    id: 'echo',
    label: 'Echo',
    description: 'Warm and engaging.',
  },
  {
    id: 'shimmer',
    label: 'Shimmer',
    description: 'Energetic and expressive.',
  },
]

export const AI_CALLER_SCRIPTS = [
  {
    id: 'iul',
    label: 'IUL - Indexed Universal Life',
    description:
      'For prospects interested in tax-advantaged growth and flexible premium payments.',
  },
  {
    id: 'ibc',
    label: 'Infinite Banking Concept',
    description:
      'For prospects interested in becoming their own bank and building generational wealth.',
  },
  {
    id: 'final_expense',
    label: 'Final Expense Insurance',
    description:
      'For prospects ages 50-85 seeking affordable burial and final expense coverage.',
  },
  {
    id: 'term',
    label: 'Term Life Insurance',
    description:
      'For prospects needing affordable, straightforward death benefit protection.',
  },
  {
    id: 'custom',
    label: 'Custom',
    description: 'Blank talk track for the agent to refine later.',
  },
]

function defaultState() {
  return {
    completed: false,
    currentStep: 0,
    voiceId: 'cedar',
    scriptId: '',
    customScript: false,
    respectDnc: true,
    reviewedCompliance: false,
    liveVoicePrompt: '',
  }
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultState()
    return { ...defaultState(), ...JSON.parse(raw) }
  } catch {
    return defaultState()
  }
}

export const aiCallerSetup = ref(load())

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(aiCallerSetup.value))
  } catch {
    /* ignore */
  }
}

export const aiCallerSetupDone = computed(() => !!aiCallerSetup.value.completed)

export function patchAiCallerSetup(partial) {
  aiCallerSetup.value = { ...aiCallerSetup.value, ...partial }
  persist()
}

export function completeAiCallerSetup() {
  patchAiCallerSetup({ completed: true, currentStep: 3 })
}

/** Dev / settings escape hatch */
export function resetAiCallerSetup() {
  aiCallerSetup.value = defaultState()
  persist()
}
