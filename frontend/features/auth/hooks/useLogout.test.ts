// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const logoutApi = vi.fn()
vi.mock('../api', () => ({
  authApi: { logout: (...args: unknown[]) => logoutApi(...args) },
}))

const clearAuth = vi.fn()
let storeState: { accessToken: string | null }
vi.mock('../store', () => ({
  useAuthStore: { getState: () => ({ ...storeState, clearAuth }) },
}))

import { useLogout } from './useLogout'

beforeEach(() => {
  logoutApi.mockReset()
  clearAuth.mockReset()
  logoutApi.mockResolvedValue(undefined)
  clearAuth.mockResolvedValue(undefined)
  storeState = { accessToken: 'access-token' }
})

describe('useLogout', () => {
  it('calls authApi.logout with the access token and clears the session', async () => {
    const { result } = renderHook(() => useLogout())

    await waitFor(() => result.current.logout())

    expect(logoutApi).toHaveBeenCalledWith('access-token')
    expect(clearAuth).toHaveBeenCalled()
  })

  it('clears the session without calling authApi.logout when there is no access token', async () => {
    storeState = { accessToken: null }
    const { result } = renderHook(() => useLogout())

    await waitFor(() => result.current.logout())

    expect(logoutApi).not.toHaveBeenCalled()
    expect(clearAuth).toHaveBeenCalled()
  })

  it('still clears the session if authApi.logout fails', async () => {
    logoutApi.mockRejectedValueOnce(new Error('network error'))
    const { result } = renderHook(() => useLogout())

    await expect(result.current.logout()).rejects.toThrow('network error')

    expect(clearAuth).toHaveBeenCalled()
  })
})
