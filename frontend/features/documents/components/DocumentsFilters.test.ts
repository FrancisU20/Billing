// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import {
  clearDocumentFilterField,
  documentFilterChips,
  emptyDocumentFilterDraft,
  toDocumentListFilters,
} from '../filters'

describe('toDocumentListFilters', () => {
  it('does not emit serie search with fewer than 3 characters', () => {
    expect(toDocumentListFilters({ ...emptyDocumentFilterDraft, serie: '00' })).toEqual({})
  })

  it('emits serie search from 3 characters', () => {
    expect(toDocumentListFilters({ ...emptyDocumentFilterDraft, serie: '001' })).toEqual({
      serie: '001',
    })
  })
})

describe('documentFilterChips', () => {
  it('returns one chip per active secondary filter', () => {
    const chips = documentFilterChips({
      ...emptyDocumentFilterDraft,
      status: 'AUTHORIZED',
      dateFrom: '2026-01-01',
    })

    expect(chips.map((chip) => chip.key)).toEqual(['status', 'date'])
  })
})

describe('clearDocumentFilterField', () => {
  it('resets only the targeted field', () => {
    const draft = {
      ...emptyDocumentFilterDraft,
      status: 'AUTHORIZED' as const,
      dateFrom: '2026-01-01',
      dateTo: '2026-02-01',
    }

    expect(clearDocumentFilterField(draft, 'status').status).toBe('all')
    const cleared = clearDocumentFilterField(draft, 'date')
    expect(cleared.dateFrom).toBe('')
    expect(cleared.dateTo).toBe('')
  })
})
