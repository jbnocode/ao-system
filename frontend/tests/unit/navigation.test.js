import { ref } from 'vue'
import { beforeEach, vi } from 'vitest'

vi.mock('@/stores/settings', () => ({
  getSettings: () => ({
    settings: ref({ life_agency_mode: 0 }),
    brand: {},
    setupBrand: () => {},
    _settings: {},
  }),
}))

vi.mock('@/router', () => ({
  default: {
    hasRoute: () => true,
  },
}))

vi.mock('@/stores/users', () => ({
  usersStore: () => ({
    isManager: () => true,
  }),
}))

import { getNavigationItems, navigationItems } from '@/utils/navigation'

describe('navigationItems', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses unique route names', () => {
    const routes = navigationItems.map((item) => item.route)
    expect(new Set(routes).size).toBe(routes.length)
  })

  it('keeps primary work above the tools divider', () => {
    const routes = navigationItems.map((item) => item.route)
    expect(routes).toEqual([
      'Dashboard',
      'Leads',
      'Deals',
      'Quoting',
      'Policies',
      'Documents',
      'Contacts',
      'Tasks',
      'Notes',
      'AI',
      'Dialer',
      'Human Dialer',
      'Text Inbox',
      'Automations',
      'Campaigns',
      'Forms',
      'Calendar',
      'Booking',
    ])
    expect(routes).not.toContain('Organizations')
    expect(routes).not.toContain('Call Logs')
    const items = getNavigationItems()
    expect(items.find((item) => item.route === 'Quoting')?.dividerBefore).toBe(
      true,
    )
    expect(items.find((item) => item.route === 'Policies')?.dividerBefore).toBe(
      false,
    )
    expect(items.find((item) => item.route === 'Dialer')?.dividerBefore).toBe(
      true,
    )
    expect(items.find((item) => item.route === 'Dialer')?.label).toBe('AI Call')
    expect(items.find((item) => item.route === 'Human Dialer')?.label).toBe(
      'Phone',
    )
    expect(
      items.find((item) => item.route === 'Automations')?.dividerBefore,
    ).toBe(false)
  })

  it('omits desktop-only destinations on mobile', () => {
    const mobileItems = getNavigationItems({ mobile: true })
    const mobileRoutes = mobileItems.map((item) => item.route)
    expect(mobileRoutes).not.toContain('Dashboard')
    expect(mobileRoutes).not.toContain('Calendar')
    expect(mobileRoutes).not.toContain('Booking')
    expect(mobileRoutes).not.toContain('Automations')
    expect(mobileRoutes).not.toContain('Campaigns')
    expect(mobileRoutes).not.toContain('Forms')
    expect(mobileRoutes).not.toContain('Call Logs')
    expect(mobileRoutes).toContain('AI')
    expect(mobileRoutes).toContain('Leads')
    expect(mobileRoutes).toContain('Quoting')
    expect(mobileRoutes).toContain('Policies')
    expect(mobileRoutes).toContain('Documents')
    expect(
      mobileItems.find((item) => item.route === 'Dialer')?.dividerBefore,
    ).toBe(true)
  })
})
