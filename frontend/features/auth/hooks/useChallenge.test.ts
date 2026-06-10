// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/errors'
import type { AuthChallenge, AuthTokens } from '../types'

const challengeFn = vi.fn()
vi.mock('../api', () => ({
  authApi: { challenge: (...args: unknown[]) => challengeFn(...args) },
}))

const setTokens = vi.fn()
vi.mock('../store', () => ({
  useAuthStore: (selector: (s: { setTokens: typeof setTokens }) => unknown) =>
    selector({ setTokens }),
}))

import { useChallenge } from './useChallenge'

const tokens: AuthTokens = {
  idToken: 'id-token',
  accessToken: 'access-token',
  refreshToken: 'refresh-token',
}

const nextChallenge: AuthChallenge = {
  challenge_name: 'MFA_SETUP',
  session: 'session-2',
  parameters: {},
}

beforeEach(() => {
  challengeFn.mockReset()
  setTokens.mockReset()
})

describe('useChallenge', () => {
  it('stores tokens and returns success when the challenge is resolved', async () => {
    challengeFn.mockResolvedValueOnce(tokens)
    const { result } = renderHook(() => useChallenge())

    let outcome
    await waitFor(async () => {
      outcome = await result.current.respond({
        session: 'session-1',
        challenge_name: 'NEW_PASSWORD_REQUIRED',
        responses: { NEW_PASSWORD: 'secret' },
      })
    })

    expect(outcome).toEqual({ type: 'success' })
    expect(setTokens).toHaveBeenCalledWith(tokens)
  })

  it('returns a follow-up challenge without storing tokens', async () => {
    challengeFn.mockResolvedValueOnce(nextChallenge)
    const { result } = renderHook(() => useChallenge())

    let outcome
    await waitFor(async () => {
      outcome = await result.current.respond({
        session: 'session-1',
        challenge_name: 'NEW_PASSWORD_REQUIRED',
        responses: { NEW_PASSWORD: 'secret' },
      })
    })

    expect(outcome).toEqual({ type: 'challenge', challenge: nextChallenge })
    expect(setTokens).not.toHaveBeenCalled()
  })

  it('maps a rejected challenge to an ApiError and rethrows it', async () => {
    challengeFn.mockRejectedValueOnce(new Error('sesión expirada'))
    const { result } = renderHook(() => useChallenge())

    await expect(
      result.current.respond({
        session: 'session-1',
        challenge_name: 'NEW_PASSWORD_REQUIRED',
        responses: {},
      }),
    ).rejects.toThrow(ApiError)

    await waitFor(() => expect(result.current.error).toBeInstanceOf(ApiError))
    expect(result.current.loading).toBe(false)
  })
})
