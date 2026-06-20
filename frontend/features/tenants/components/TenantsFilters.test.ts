// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import {
  clearTenantFilterField,
  emptyTenantFilterDraft,
  tenantFilterChips,
  toTenantListFilters,
} from '../filters'

describe('toTenantListFilters', () => {
  it('does not emit remote search filters with fewer than 3 characters', () => {
    expect(toTenantListFilters({ ...emptyTenantFilterDraft, search: 'ab' })).toEqual({})
  })

  it('emits general search from 3 characters', () => {
    expect(toTenantListFilters({ ...emptyTenantFilterDraft, search: 'abc' })).toEqual({
      q: 'abc',
    })
  })

  it('emits RUC search from 3 characters', () => {
    expect(
      toTenantListFilters({
        ...emptyTenantFilterDraft,
        searchMode: 'ruc',
        search: '179',
      }),
    ).toEqual({ ruc: '179' })
  })
})

describe('tenantFilterChips', () => {
  it('returns one chip per active secondary filter', () => {
    const chips = tenantFilterChips({
      ...emptyTenantFilterDraft,
      status: 'suspended',
      sriEnvironment: 'production',
      planStatus: 'expired',
      createdTo: '2026-03-01',
    })

    expect(chips.map((chip) => chip.key)).toEqual([
      'status',
      'sriEnvironment',
      'planStatus',
      'created',
    ])
  })
})

describe('clearTenantFilterField', () => {
  it('resets only the targeted field', () => {
    const draft = {
      ...emptyTenantFilterDraft,
      status: 'suspended' as const,
      sriEnvironment: 'production' as const,
      planStatus: 'expired' as const,
    }

    expect(clearTenantFilterField(draft, 'status').status).toBe('all')
    expect(clearTenantFilterField(draft, 'sriEnvironment').sriEnvironment).toBe('all')
    expect(clearTenantFilterField(draft, 'planStatus').planStatus).toBe('all')
  })
})
