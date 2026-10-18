import { describe, expect, it } from 'vitest'

/** Mirrors crm.life.journey status maps for UI hints. */
const QUOTE_STATUS_TO_DEAL = {
  Presented: 'Quoted',
  Accepted: 'Application Submitted',
}
const APPLICATION_STATUS_TO_DEAL = {
  Submitted: 'Application Submitted',
  Underwriting: 'Underwriting',
  Approved: 'Approved',
  Issued: 'Policy Delivered',
  Declined: 'Declined',
}
const POLICY_STATUS_TO_DEAL = {
  Pending: 'Approved',
  'In Force': 'Policy Delivered',
  Lapsed: 'Lost',
  Cancelled: 'Lost',
}

describe('life journey status hints', () => {
  it('maps accepted quote to application submitted', () => {
    expect(QUOTE_STATUS_TO_DEAL.Accepted).toBe('Application Submitted')
  })

  it('maps underwriting application', () => {
    expect(APPLICATION_STATUS_TO_DEAL.Underwriting).toBe('Underwriting')
  })

  it('maps in-force policy to delivered', () => {
    expect(POLICY_STATUS_TO_DEAL['In Force']).toBe('Policy Delivered')
  })
})
