// @vitest-environment jsdom
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useLocalPagedItems } from './useLocalPagedItems'

describe('useLocalPagedItems', () => {
  it('slices items by page and page size', () => {
    const items = Array.from({ length: 12 }, (_, index) => index + 1)
    const { result } = renderHook(() => useLocalPagedItems(items, 10))

    expect(result.current.pageItems).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(result.current.totalPages).toBe(2)

    act(() => result.current.nextPage())

    expect(result.current.page).toBe(2)
    expect(result.current.pageItems).toEqual([11, 12])
  })

  it('resets to the first page when page size changes', () => {
    const items = Array.from({ length: 30 }, (_, index) => index + 1)
    const { result } = renderHook(() => useLocalPagedItems(items, 10))

    act(() => result.current.nextPage())
    expect(result.current.page).toBe(2)

    act(() => result.current.setPageSize(25))

    expect(result.current.page).toBe(1)
    expect(result.current.pageSize).toBe(25)
    expect(result.current.pageItems).toHaveLength(25)
  })

  it('jumps to an arbitrary page within range', () => {
    const items = Array.from({ length: 95 }, (_, index) => index + 1)
    const { result } = renderHook(() => useLocalPagedItems(items, 10))

    act(() => result.current.goToPage(7))

    expect(result.current.page).toBe(7)
    expect(result.current.pageItems).toEqual([61, 62, 63, 64, 65, 66, 67, 68, 69, 70])
  })

  it('clamps goToPage to the valid range', () => {
    const items = Array.from({ length: 25 }, (_, index) => index + 1)
    const { result } = renderHook(() => useLocalPagedItems(items, 10))

    act(() => result.current.goToPage(999))
    expect(result.current.page).toBe(3)

    act(() => result.current.goToPage(-5))
    expect(result.current.page).toBe(1)

    act(() => result.current.goToPage(Number.NaN))
    expect(result.current.page).toBe(1)
  })
})
