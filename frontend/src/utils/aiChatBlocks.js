/**
 * Normalize AI chat `blocks` from the server into renderable shapes.
 * Supports `type: "insurance"` (Deal-style cards) and `type: "table"`.
 */

export function normalizeChatBlocks(blocks = []) {
  if (!Array.isArray(blocks)) return []
  return blocks
    .map((raw) => normalizeBlock(raw))
    .filter(Boolean)
}

function normalizeBlock(raw) {
  if (!raw || typeof raw !== 'object') return null
  const type = String(raw.type || '').toLowerCase()
  if (type === 'insurance') return normalizeInsurance(raw)
  if (type === 'table') {
    // Legacy string tables that look like insurance → upgrade when possible
    const asInsurance = tableToInsurance(raw)
    if (asInsurance) return asInsurance
    return normalizeTable(raw)
  }
  return null
}

function normalizeInsurance(raw) {
  const items = Array.isArray(raw.items)
    ? raw.items.map(normalizeInsuranceItem).filter(Boolean)
    : []
  if (!items.length) return null
  const kind = raw.kind || 'Quotes'
  const tab =
    raw.tab ||
    (kind === 'Policies' ? 'policies' : kind === 'Catalog' ? 'quotes' : 'quotes')
  return {
    type: 'insurance',
    kind,
    tab,
    title: raw.title ? String(raw.title) : '',
    items,
  }
}

function normalizeInsuranceItem(item) {
  if (!item || typeof item !== 'object') return null
  return {
    name: item.name ? String(item.name) : '',
    deal: item.deal ? String(item.deal) : '',
    carrier: item.carrier != null ? String(item.carrier) : '',
    product: item.product != null ? String(item.product) : '',
    face_amount: Number(item.face_amount) || 0,
    monthly_premium: Number(item.monthly_premium) || 0,
    term_years: item.term_years != null ? item.term_years : null,
    policy_number: item.policy_number ? String(item.policy_number) : '',
    status: item.status ? String(item.status) : '',
    quote_date: item.quote_date || '',
    effective_date: item.effective_date || '',
  }
}

function normalizeTable(raw) {
  const columns = Array.isArray(raw.columns)
    ? raw.columns.map((c) => String(c ?? ''))
    : []
  const rows = Array.isArray(raw.rows)
    ? raw.rows.map((row) => {
        if (Array.isArray(row)) return row.map((cell) => String(cell ?? ''))
        if (row && typeof row === 'object') {
          return columns.map((col) =>
            String(row[col] ?? row[col.toLowerCase()] ?? ''),
          )
        }
        return [String(row ?? '')]
      })
    : []
  if (!columns.length && !rows.length) return null
  return {
    type: 'table',
    title: raw.title ? String(raw.title) : '',
    columns,
    rows,
  }
}

/** Best-effort: old column/row insurance tables → insurance cards */
function tableToInsurance(raw) {
  const columns = (raw.columns || []).map((c) => String(c).toLowerCase())
  if (!columns.includes('carrier')) return null
  const idx = (name) => columns.indexOf(name)
  const rows = Array.isArray(raw.rows) ? raw.rows : []
  const items = rows
    .map((row) => {
      if (!Array.isArray(row)) return null
      const get = (name) => {
        const i = idx(name)
        return i >= 0 ? row[i] : ''
      }
      const faceRaw = String(get('face') || get('face amount') || '').replace(
        /[^0-9.]/g,
        '',
      )
      const premRaw = String(
        get('monthly') || get('monthly premium') || '',
      ).replace(/[^0-9.]/g, '')
      return {
        carrier: get('carrier'),
        product: get('product'),
        face_amount: Number(faceRaw) || 0,
        monthly_premium: Number(premRaw) || 0,
        term_years: get('term') || null,
        status: get('status') || '',
        deal: get('deal') || '',
        policy_number: get('policy #') || get('policy') || '',
      }
    })
    .filter(Boolean)
  if (!items.length) return null
  const kind = columns.includes('policy #') ? 'Policies' : 'Quotes'
  return normalizeInsurance({
    type: 'insurance',
    kind,
    tab: kind === 'Policies' ? 'policies' : 'quotes',
    title: raw.title,
    items,
  })
}
