import { computed } from 'vue'
import { getSettings } from '@/stores/settings'

/** Person-first Cases UX when FCRM Settings.life_agency_mode is on. */
export function useLifeAgencyMode() {
  const { settings, _settings } = getSettings()

  // Document resources use reload()/get — not fetch() (that's createResource).
  if (!_settings.doc && !_settings.get?.loading) {
    _settings.reload?.()
  }

  const lifeAgencyMode = computed(
    () => !!(settings.value?.life_agency_mode ?? _settings.doc?.life_agency_mode),
  )

  const dealsLabel = computed(() =>
    lifeAgencyMode.value ? __('Cases') : __('Deals'),
  )

  const dealSingular = computed(() =>
    lifeAgencyMode.value ? __('Case') : __('Deal'),
  )

  return {
    lifeAgencyMode,
    dealsLabel,
    dealSingular,
  }
}
