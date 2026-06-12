// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/errors'
import { useFormSubmit } from './useFormSubmit'

describe('useFormSubmit', () => {
  it('starts as not submitting and without error', () => {
    const action = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useFormSubmit(action))

    expect(result.current.submitting).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('runs the action and resets submitting on success', async () => {
    const action = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() => useFormSubmit(action))

    await act(async () => {
      await result.current.submit('value')
    })

    expect(action).toHaveBeenCalledWith('value')
    expect(result.current.submitting).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('maps a rejected action to an ApiError', async () => {
    const action = vi.fn().mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useFormSubmit(action))

    await act(async () => {
      await result.current.submit()
    })

    expect(result.current.submitting).toBe(false)
    expect(result.current.error).toBeInstanceOf(ApiError)
    expect(result.current.error?.message).toBe('boom')
  })

  it('clears a previous error on the next submit', async () => {
    const action = vi.fn().mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(undefined)
    const { result } = renderHook(() => useFormSubmit(action))

    await act(async () => {
      await result.current.submit()
    })
    expect(result.current.error).toBeInstanceOf(ApiError)

    await act(async () => {
      await result.current.submit()
    })
    expect(result.current.error).toBeNull()
  })
})
