// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Plan } from '../types'

const getBySlug = vi.fn()
const adminGetBySlug = vi.fn()
vi.mock('../api', () => ({
  plansApi: {
    getBySlug: (...args: unknown[]) => getBySlug(...args),
    adminGetBySlug: (...args: unknown[]) => adminGetBySlug(...args),
  },
}))

import { useAdminPlan, usePlan } from './usePlan'

const plan = { id: 'plan-1', slug: 'profesional' } as unknown as Plan

beforeEach(() => {
  getBySlug.mockReset()
  adminGetBySlug.mockReset()
})

describe('usePlan', () => {
  it('does not fetch when slug is null', () => {
    const { result } = renderHook(() => usePlan(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.plan).toBeNull()
    expect(getBySlug).not.toHaveBeenCalled()
  })

  it('loads the plan via the public endpoint', async () => {
    getBySlug.mockResolvedValueOnce(plan)
    const { result } = renderHook(() => usePlan('profesional'))

    await waitFor(() => expect(result.current.plan).toEqual(plan))
    expect(getBySlug).toHaveBeenCalledWith('profesional')
    expect(adminGetBySlug).not.toHaveBeenCalled()
  })
})

describe('useAdminPlan', () => {
  it('loads the plan via the admin endpoint', async () => {
    adminGetBySlug.mockResolvedValueOnce(plan)
    const { result } = renderHook(() => useAdminPlan('profesional'))

    await waitFor(() => expect(result.current.plan).toEqual(plan))
    expect(adminGetBySlug).toHaveBeenCalledWith('profesional')
    expect(getBySlug).not.toHaveBeenCalled()
  })
})
