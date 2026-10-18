import { computed, ref } from 'vue'

export const mobileSidebarOpened = ref(false)

export const isMobileView = computed(() => window.innerWidth < 768)

export const showSettings = ref(false)

export const disableSettingModalOutsideClick = ref(false)

export const activeSettingsPage = ref('')

/** When opening Telephony settings, jump to this sub-step (e.g. phone-numbers). */
export const telephonySettingsStep = ref('')

/** Optional user filter when opening Settings → Usage from Credits. */
export const creditUsageUserFilter = ref('')
