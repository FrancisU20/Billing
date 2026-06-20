// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import {
  clearClientFilterField,
  clientFilterChips,
  emptyClientFilterDraft,
  toClientListFilters,
} from '../filters'

describe('toClientListFilters', () => {
  it('does not emit remote search filters with fewer than 3 characters', () => {
    expect(toClientListFilters({ ...emptyClientFilterDraft, search: 'ab' })).toEqual({})
  })

  it('emits general search from 3 characters', () => {
    expect(toClientListFilters({ ...emptyClientFilterDraft, search: 'abc' })).toEqual({
      q: 'abc',
    })
  })

  it('emits exact identification search from 3 characters', () => {
    expect(
      toClientListFilters({
        ...emptyClientFilterDraft,
        searchMode: 'identification',
        search: '179',
      }),
    ).toEqual({ identification: '179' })
  })
})

describe('clientFilterChips', () => {
  it('returns no chips when only the search field is set', () => {
    expect(clientFilterChips({ ...emptyClientFilterDraft, search: 'abc' })).toEqual([])
  })

  it('returns one chip per active secondary filter', () => {
    const chips = clientFilterChips({
      ...emptyClientFilterDraft,
      status: 'active',
      identificationType: 'ruc',
      createdFrom: '2026-01-01',
    })

    expect(chips.map((chip) => chip.key)).toEqual(['status', 'identificationType', 'created'])
  })
})

describe('clearClientFilterField', () => {
  it('resets only the targeted field', () => {
    const draft = {
      ...emptyClientFilterDraft,
      status: 'active' as const,
      identificationType: 'ruc' as const,
      createdFrom: '2026-01-01',
      createdTo: '2026-02-01',
    }

    expect(clearClientFilterField(draft, 'status').status).toBe('all')
    expect(clearClientFilterField(draft, 'identificationType').identificationType).toBe('all')
    const cleared = clearClientFilterField(draft, 'created')
    expect(cleared.createdFrom).toBe('')
    expect(cleared.createdTo).toBe('')
  })
})
