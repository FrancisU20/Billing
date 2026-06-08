import { afterEach, describe, expect, it, vi } from 'vitest'
import { z } from 'zod'

vi.mock('expo-constants', () => ({
  default: { expoConfig: { extra: { apiUrl: 'http://api.test' } } },
}))

import { api, configureApiClient } from './client'
import { ApiError } from './errors'

function mockFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    status,
    json: vi.fn().mockResolvedValue(body),
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('api client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    configureApiClient({
      getIdToken: () => null,
      onRefresh: async () => false,
      onSessionExpired: () => undefined,
    })
  })

  it('parses successful envelope data with the endpoint schema', async () => {
    mockFetch({
      success: true,
      data: { id: '1' },
      error: null,
      meta: { request_id: 'req', timestamp: 'now' },
    })

    await expect(api.get('/resource', z.object({ id: z.string() }))).resolves.toEqual({ id: '1' })
  })

  it('rejects invalid successful data', async () => {
    mockFetch({
      success: true,
      data: { id: 1 },
      error: null,
      meta: { request_id: 'req', timestamp: 'now' },
    })

    await expect(api.get('/resource', z.object({ id: z.string() }))).rejects.toThrow()
  })

  it('maps API error envelopes to ApiError', async () => {
    mockFetch(
      {
        success: false,
        data: null,
        error: { code: 'VALIDATION_ERROR', message: 'Bad payload' },
        meta: { request_id: 'req', timestamp: 'now' },
      },
      400,
    )

    await expect(api.get('/resource', z.object({ id: z.string() }))).rejects.toBeInstanceOf(
      ApiError,
    )
  })
})
