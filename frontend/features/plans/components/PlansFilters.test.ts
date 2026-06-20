// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import {
  clearPlanFilterField,
  emptyPlanFilterDraft,
  planFilterChips,
  toPlanListFilters,
} from '../filters'

describe('toPlanListFilters', () => {
  it('does not emit remote search filters with fewer than 3 characters', () => {
    expect(toPlanListFilters({ ...emptyPlanFilterDraft, search: 'ab' })).toEqual({})
  })

  it('emits general search from 3 characters', () => {
    expect(toPlanListFilters({ ...emptyPlanFilterDraft, search: 'abc' })).toEqual({ q: 'abc' })
  })

  it('emits slug search from 3 characters', () => {
    expect(
      toPlanListFilters({
        ...emptyPlanFilterDraft,
        searchMode: 'slug',
        search: 'pro',
      }),
    ).toEqual({ slug: 'pro' })
  })
})

describe('planFilterChips', () => {
  it('returns one chip per active secondary filter', () => {
    const chips = planFilterChips({
      ...emptyPlanFilterDraft,
      status: 'active',
      limitCycle: 'year',
      createdFrom: '2026-01-01',
    })

    expect(chips.map((chip) => chip.key)).toEqual(['status', 'limitCycle', 'created'])
  })
})

describe('clearPlanFilterField', () => {
  it('resets only the targeted field', () => {
    const draft = {
      ...emptyPlanFilterDraft,
      status: 'active' as const,
      limitCycle: 'year' as const,
    }

    expect(clearPlanFilterField(draft, 'status').status).toBe('all')
    expect(clearPlanFilterField(draft, 'limitCycle').limitCycle).toBe('all')
  })
})
