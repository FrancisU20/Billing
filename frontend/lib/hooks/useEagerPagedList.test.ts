// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useEagerPagedList } from './useEagerPagedList'

describe('useEagerPagedList', () => {
  const loadPage = vi.fn()
  const filters = {}

  beforeEach(() => {
    loadPage.mockReset()
  })

  it('sweeps every page sequentially and paginates the full set locally', async () => {
    const pageA = Array.from({ length: 50 }, (_, i) => i + 1)
    const pageB = Array.from({ length: 50 }, (_, i) => i + 51)
    const pageC = [101]
    loadPage
      .mockResolvedValueOnce({ items: pageA, next_token: 'cursor-2', has_more: true, total: 101 })
      .mockResolvedValueOnce({ items: pageB, next_token: 'cursor-3', has_more: true, total: 101 })
      .mockResolvedValueOnce({ items: pageC, next_token: null, has_more: false, total: 101 })

    const { result } = renderHook(() => useEagerPagedList(filters, loadPage, 10))

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(loadPage).toHaveBeenCalledTimes(3)
    expect(loadPage).toHaveBeenNthCalledWith(1, filters, undefined, 50)
    expect(loadPage).toHaveBeenNthCalledWith(2, filters, 'cursor-2', 50)
    expect(loadPage).toHaveBeenNthCalledWith(3, filters, 'cursor-3', 50)
    expect(result.current.totalItems).toBe(101)
    expect(result.current.backendTotal).toBe(101)
    expect(result.current.truncated).toBe(false)
    expect(result.current.pageItems).toEqual(pageA.slice(0, 10))
    expect(result.current.totalPages).toBe(11)
  })

  it('jumps to an arbitrary page once the full set is loaded', async () => {
    const items = Array.from({ length: 25 }, (_, i) => i + 1)
    loadPage.mockResolvedValueOnce({ items, next_token: null, has_more: false })

    const { result } = renderHook(() => useEagerPagedList(filters, loadPage, 10))
    await waitFor(() => expect(result.current.loading).toBe(false))

    act(() => result.current.goToPage(3))

    expect(result.current.page).toBe(3)
    expect(result.current.pageItems).toEqual([21, 22, 23, 24, 25])
  })

  it('marks the set as truncated when the safety cap of pages is hit', async () => {
    loadPage.mockImplementation(() =>
      Promise.resolve({ items: [1], next_token: 'next', has_more: true }),
    )

    const { result } = renderHook(() => useEagerPagedList(filters, loadPage))
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(loadPage).toHaveBeenCalledTimes(20)
    expect(result.current.truncated).toBe(true)
    expect(result.current.totalItems).toBe(20)
  })

  it('re-sweeps from scratch when filters change', async () => {
    loadPage
      .mockResolvedValueOnce({ items: [1], next_token: null, has_more: false })
      .mockResolvedValueOnce({ items: [2, 3], next_token: null, has_more: false })

    const { result, rerender } = renderHook(({ f }) => useEagerPagedList(f, loadPage), {
      initialProps: { f: { q: 'a' } },
    })
    await waitFor(() => expect(result.current.totalItems).toBe(1))

    rerender({ f: { q: 'b' } })
    await waitFor(() => expect(result.current.totalItems).toBe(2))

    expect(loadPage).toHaveBeenCalledTimes(2)
  })
})
