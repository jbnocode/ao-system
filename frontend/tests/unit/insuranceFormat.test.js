import { describe, expect, it } from 'vitest'
import {
  formatInsuranceMoney,
  insuranceStatusTheme,
} from '@/utils/insuranceFormat'

describe('insuranceFormat', () => {
  it('formats money as USD without cents', () => {
    expect(formatInsuranceMoney(500000)).toBe('$500,000')
    expect(formatInsuranceMoney(null)).toBe('$0')
  })

  it('maps status themes', () => {
    expect(insuranceStatusTheme('In Force')).toBe('green')
    expect(insuranceStatusTheme('Declined')).toBe('red')
    expect(insuranceStatusTheme('Presented')).toBe('blue')
    expect(insuranceStatusTheme('Draft')).toBe('gray')
  })
})
