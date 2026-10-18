/** Shared formatters for Quoting / Policies list pages. */

export function formatInsuranceMoney(v) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(Number(v) || 0)
}

export function insuranceStatusTheme(status) {
  if (['Accepted', 'Approved', 'Issued', 'In Force'].includes(status)) {
    return 'green'
  }
  if (['Declined', 'Lapsed', 'Cancelled'].includes(status)) {
    return 'red'
  }
  if (
    ['Presented', 'Submitted', 'Underwriting', 'Pending'].includes(status)
  ) {
    return 'blue'
  }
  return 'gray'
}
