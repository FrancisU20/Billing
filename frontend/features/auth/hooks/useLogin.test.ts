// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/errors'
import type { AuthChallenge, AuthTokens } from '../types'

const login = vi.fn()
vi.mock('../api', () => ({
  authApi: { login: (...args: unknown[]) => login(...args) },
}))

const setTokens = vi.fn()
vi.mock('../store', () => ({
  useAuthStore: (selector: (s: { setTokens: typeof setTokens }) => unknown) =>
    selector({ setTokens }),
}))

import { useLogin } from './useLogin'

const tokens: AuthTokens = {
  idToken: 'id-token',
  accessToken: 'access-token',
  refreshToken: 'refresh-token',
}

const challenge: AuthChallenge = {
  challenge_name: 'NEW_PASSWORD_REQUIRED',
  session: 'session-1',
  parameters: {},
}

beforeEach(() => {
  login.mockReset()
  setTokens.mockReset()
})

describe('useLogin', () => {
  it('stores tokens and returns success on a normal login', async () => {
    login.mockResolvedValueOnce(tokens)
    const { result } = renderHook(() => useLogin())

    let outcome
    await waitFor(async () => {
      outcome = await result.current.login({ username: 'a@b.com', password: 'secret' })
    })

    expect(outcome).toEqual({ type: 'success' })
    expect(setTokens).toHaveBeenCalledWith(tokens)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('returns a challenge without storing tokens', async () => {
    login.mockResolvedValueOnce(challenge)
    const { result } = renderHook(() => useLogin())

    let outcome
    await waitFor(async () => {
      outcome = await result.current.login({ username: 'a@b.com', password: 'secret' })
    })

    expect(outcome).toEqual({ type: 'challenge', challenge })
    expect(setTokens).not.toHaveBeenCalled()
  })

  it('maps a rejected login to an ApiError and rethrows it', async () => {
    login.mockRejectedValueOnce(new Error('credenciales inválidas'))
    const { result } = renderHook(() => useLogin())

    await expect(result.current.login({ username: 'a@b.com', password: 'bad' })).rejects.toThrow(
      ApiError,
    )

    await waitFor(() => expect(result.current.error).toBeInstanceOf(ApiError))
    expect(result.current.loading).toBe(false)
  })
})
