// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useRefreshOnFocus } from './useRefreshOnFocus'

const navigationMock = vi.hoisted(() => ({
  addListener: vi.fn(),
  focusHandler: undefined as (() => void) | undefined,
  unsubscribe: vi.fn(),
}))

vi.mock('expo-router', () => ({
  useNavigation: () => ({
    addListener: navigationMock.addListener,
  }),
}))

describe('useRefreshOnFocus', () => {
  beforeEach(() => {
    navigationMock.focusHandler = undefined
    navigationMock.unsubscribe.mockReset()
    navigationMock.addListener.mockReset()
    navigationMock.addListener.mockImplementation((event: string, handler: () => void) => {
      if (event === 'focus') navigationMock.focusHandler = handler
      return navigationMock.unsubscribe
    })
  })

  it('skips the initial focus event by default and refreshes on subsequent focus', () => {
    const refresh = vi.fn()

    renderHook(() => useRefreshOnFocus(refresh))

    act(() => navigationMock.focusHandler?.())
    expect(refresh).not.toHaveBeenCalled()

    act(() => navigationMock.focusHandler?.())
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('can refresh on the first focus event when skipInitial is disabled', () => {
    const refresh = vi.fn()

    renderHook(() => useRefreshOnFocus(refresh, { skipInitial: false }))

    act(() => navigationMock.focusHandler?.())
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('does not subscribe when disabled', () => {
    const refresh = vi.fn()

    renderHook(() => useRefreshOnFocus(refresh, { enabled: false }))

    expect(navigationMock.addListener).not.toHaveBeenCalled()
  })
})
