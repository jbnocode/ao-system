import { describe, expect, it } from 'vitest'
import { normalizeChatBlocks } from '../../src/utils/aiChatBlocks'

describe('normalizeChatBlocks', () => {
  it('returns empty for non-arrays', () => {
    expect(normalizeChatBlocks(null)).toEqual([])
    expect(normalizeChatBlocks(undefined)).toEqual([])
    expect(normalizeChatBlocks({})).toEqual([])
  })

  it('normalizes insurance blocks', () => {
    const blocks = normalizeChatBlocks([
      {
        type: 'insurance',
        kind: 'Quotes',
        tab: 'quotes',
        title: 'Quotes on file',
        items: [
          {
            name: 'IQ-1',
            deal: 'CRM-DEAL-1',
            carrier: 'Protective',
            product: 'Term 20',
            face_amount: 500000,
            monthly_premium: 48.2,
            status: 'Presented',
          },
        ],
      },
    ])
    expect(blocks).toHaveLength(1)
    expect(blocks[0].type).toBe('insurance')
    expect(blocks[0].items[0].deal).toBe('CRM-DEAL-1')
    expect(blocks[0].items[0].face_amount).toBe(500000)
  })

  it('upgrades legacy carrier tables to insurance cards', () => {
    const blocks = normalizeChatBlocks([
      {
        type: 'table',
        title: 'Quotes',
        columns: ['Carrier', 'Product', 'Face', 'Monthly', 'Deal'],
        rows: [['Protective', 'Term', '$500,000', '$48.20', 'DEAL-1']],
      },
    ])
    expect(blocks[0].type).toBe('insurance')
    expect(blocks[0].items[0].carrier).toBe('Protective')
    expect(blocks[0].items[0].deal).toBe('DEAL-1')
  })

  it('keeps generic tables', () => {
    const blocks = normalizeChatBlocks([
      {
        type: 'table',
        title: 'Misc',
        columns: ['A', 'B'],
        rows: [['1', '2']],
      },
    ])
    expect(blocks[0]).toEqual({
      type: 'table',
      title: 'Misc',
      columns: ['A', 'B'],
      rows: [['1', '2']],
    })
  })

  it('drops empty tables', () => {
    expect(normalizeChatBlocks([{ type: 'table', columns: [], rows: [] }])).toEqual(
      [],
    )
  })
})
