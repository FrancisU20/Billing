// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Plan, PlanListFilters } from '../types'

const list = vi.fn()
const adminList = vi.fn()
vi.mock('../api', () => ({
  plansApi: {
    list: (...args: unknown[]) => list(...args),
    adminList: (...args: unknown[]) => adminList(...args),
  },
}))

import { useAdminPlans, usePlans } from './usePlans'

const planA = { id: 'a', order: 2 } as unknown as Plan
const planB = { id: 'b', order: 1 } as unknown as Plan

beforeEach(() => {
  list.mockReset()
  adminList.mockReset()
})

describe('usePlans', () => {
  it('loads public plans sorted by order', async () => {
    list.mockResolvedValueOnce({ items: [planA, planB], next_token: null, has_more: false })
    const { result } = renderHook(() => usePlans())

    expect(result.current.loading).toBe(true)
    expect(result.current.plans).toEqual([])

    await waitFor(() => expect(result.current.plans).toEqual([planB, planA]))
  })
})

describe('useAdminPlans', () => {
  it('loads admin plans with filters and sorts by order', async () => {
    adminList.mockResolvedValueOnce({ items: [planA, planB], next_token: null, has_more: false })
    const filters = { status: 'active' as const }
    const { result } = renderHook(() => useAdminPlans(filters))

    await waitFor(() => expect(result.current.plans).toEqual([planB, planA]))
    expect(adminList).toHaveBeenCalledWith(filters)
  })

  it('refetches when filters change', async () => {
    adminList
      .mockResolvedValueOnce({ items: [planA], next_token: null, has_more: false })
      .mockResolvedValueOnce({ items: [planB], next_token: null, has_more: false })

    const { result, rerender } = renderHook(
      ({ filters }: { filters: PlanListFilters }) => useAdminPlans(filters),
      { initialProps: { filters: { status: 'active' } } },
    )

    await waitFor(() => expect(result.current.plans).toEqual([planA]))

    rerender({ filters: { status: 'inactive' } })

    await waitFor(() => expect(result.current.plans).toEqual([planB]))
    expect(adminList).toHaveBeenCalledTimes(2)
  })
})
