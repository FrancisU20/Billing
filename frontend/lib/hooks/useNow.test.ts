// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useNow } from './useNow'

describe('useNow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns the current time on mount', () => {
    vi.setSystemTime(new Date('2026-06-20T10:00:00Z'))

    const { result } = renderHook(() => useNow())

    expect(result.current.toISOString()).toBe('2026-06-20T10:00:00.000Z')
  })

  it('ticks every 30s without requiring a re-render trigger from the caller', () => {
    vi.setSystemTime(new Date('2026-06-20T10:00:00Z'))
    const { result } = renderHook(() => useNow())

    act(() => {
      vi.advanceTimersByTime(30_000)
    })

    expect(result.current.toISOString()).toBe('2026-06-20T10:00:30.000Z')
  })
})
