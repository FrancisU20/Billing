// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Client } from '../types'

const getById = vi.fn()
vi.mock('../api', () => ({
  clientsApi: { getById: (...args: unknown[]) => getById(...args) },
}))

import { useClient } from './useClient'

const client = { id: 'client-1', trade_name: 'Cliente Demo' } as unknown as Client

describe('useClient', () => {
  beforeEach(() => {
    getById.mockReset()
  })

  it('does not fetch when id is null', () => {
    const { result } = renderHook(() => useClient(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.client).toBeNull()
    expect(getById).not.toHaveBeenCalled()
  })

  it('loads the client by id', async () => {
    getById.mockResolvedValueOnce(client)
    const { result } = renderHook(() => useClient('client-1'))

    expect(result.current.loading).toBe(true)

    await waitFor(() => expect(result.current.client).toEqual(client))
    expect(getById).toHaveBeenCalledWith('client-1')
  })

  it('refresh re-fetches the client', async () => {
    getById.mockResolvedValueOnce(client).mockResolvedValueOnce({ ...client, trade_name: 'Nuevo' })
    const { result } = renderHook(() => useClient('client-1'))

    await waitFor(() => expect(result.current.client).toEqual(client))

    result.current.refresh()

    await waitFor(() => expect(result.current.client?.trade_name).toBe('Nuevo'))
    expect(getById).toHaveBeenCalledTimes(2)
  })
})
