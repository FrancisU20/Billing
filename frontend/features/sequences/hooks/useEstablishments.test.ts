// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Establishment } from '../types'

const list = vi.fn()
vi.mock('../api', () => ({
  sequencesApi: { list: (...args: unknown[]) => list(...args) },
}))

import { useEstablishments } from './useEstablishments'

const establishment = {
  code: '001',
  label: 'Matriz',
  emission_points: [],
} as unknown as Establishment

beforeEach(() => {
  list.mockReset()
})

describe('useEstablishments', () => {
  it('does not fetch when tenantId is null', () => {
    const { result } = renderHook(() => useEstablishments(null))
    expect(result.current.loading).toBe(false)
    expect(result.current.establishments).toEqual([])
    expect(list).not.toHaveBeenCalled()
  })

  it('loads establishments for the tenant', async () => {
    list.mockResolvedValueOnce({ items: [establishment] })
    const { result } = renderHook(() => useEstablishments('tenant-1'))

    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.establishments).toEqual([establishment]))
    expect(list).toHaveBeenCalledWith('tenant-1')
  })
})
