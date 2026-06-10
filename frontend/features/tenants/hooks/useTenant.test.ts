// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Tenant } from '../types'

const getById = vi.fn()
vi.mock('../api', () => ({
  tenantsApi: { getById: (...args: unknown[]) => getById(...args) },
}))

import { useTenant } from './useTenant'

const tenant = { id: 'tenant-1', trade_name: 'Empresa Demo' } as unknown as Tenant

describe('useTenant', () => {
  beforeEach(() => {
    getById.mockReset()
  })

  it('does not fetch when id is null', () => {
    const { result } = renderHook(() => useTenant(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.tenant).toBeNull()
    expect(getById).not.toHaveBeenCalled()
  })

  it('loads the tenant by id', async () => {
    getById.mockResolvedValueOnce(tenant)
    const { result } = renderHook(() => useTenant('tenant-1'))

    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.tenant).toEqual(tenant))
    expect(getById).toHaveBeenCalledWith('tenant-1')
  })

  it('refresh re-fetches the tenant', async () => {
    getById
      .mockResolvedValueOnce(tenant)
      .mockResolvedValueOnce({ ...tenant, trade_name: 'Nueva Empresa' })
    const { result } = renderHook(() => useTenant('tenant-1'))

    await waitFor(() => expect(result.current.tenant).toEqual(tenant))

    result.current.refresh()

    await waitFor(() => expect(result.current.tenant?.trade_name).toBe('Nueva Empresa'))
    expect(getById).toHaveBeenCalledTimes(2)
  })
})
