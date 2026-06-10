// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/errors'
import { useFetch } from './useFetch'

describe('useFetch', () => {
  it('starts loading and resolves with data', async () => {
    const fetcher = vi.fn().mockResolvedValue({ id: '1' })
    const { result } = renderHook(() => useFetch(fetcher))

    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toEqual({ id: '1' })
    expect(result.current.error).toBeNull()
  })

  it('does not fetch and reports loading=false when fetcher is null', () => {
    const { result } = renderHook(() => useFetch<{ id: string }>(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('maps a rejected fetcher to an ApiError', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useFetch(fetcher))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeInstanceOf(ApiError)
    expect(result.current.error?.message).toBe('boom')
  })

  it('refresh re-runs the fetcher', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ id: '1' }).mockResolvedValueOnce({ id: '2' })
    const { result } = renderHook(() => useFetch(fetcher))

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ id: '1' })

    result.current.refresh()

    await waitFor(() => expect(result.current.data).toEqual({ id: '2' }))
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('switches from null to a fetcher and loads data', async () => {
    const fetcher = vi.fn().mockResolvedValue({ id: '1' })
    const { result, rerender } = renderHook(
      ({ f }: { f: (() => Promise<{ id: string }>) | null }) => useFetch(f),
      {
        initialProps: { f: null as (() => Promise<{ id: string }>) | null },
      },
    )

    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBeNull()

    rerender({ f: fetcher })

    await waitFor(() => expect(result.current.data).toEqual({ id: '1' }))
  })
})
