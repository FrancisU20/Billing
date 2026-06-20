// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCursorPagedList } from './useCursorPagedList'

const itemA = { id: 'a' }
const itemB = { id: 'b' }

describe('useCursorPagedList', () => {
  const loadPage = vi.fn()
  const emptyFilters = {}

  beforeEach(() => {
    loadPage.mockReset()
  })

  it('loads the first page with default page size', async () => {
    const filters = { q: 'abc' }
    loadPage.mockResolvedValueOnce({ items: [itemA], next_token: 'cursor-2', has_more: true })

    const { result } = renderHook(() => useCursorPagedList(filters, loadPage))

    await waitFor(() => expect(result.current.items).toEqual([itemA]))
    expect(loadPage).toHaveBeenCalledWith(filters, undefined, 10)
    expect(result.current.page).toBe(1)
    expect(result.current.canGoNext).toBe(true)
    expect(result.current.canGoPrevious).toBe(false)
  })

  it('moves forward and backward using stored cursors', async () => {
    loadPage
      .mockResolvedValueOnce({ items: [itemA], next_token: 'cursor-2', has_more: true })
      .mockResolvedValueOnce({ items: [itemB], next_token: null, has_more: false })
      .mockResolvedValueOnce({ items: [itemA], next_token: 'cursor-2', has_more: true })

    const { result } = renderHook(() => useCursorPagedList(emptyFilters, loadPage))
    await waitFor(() => expect(result.current.items).toEqual([itemA]))

    await act(async () => {
      await result.current.nextPage()
    })

    await waitFor(() => expect(result.current.items).toEqual([itemB]))
    expect(loadPage).toHaveBeenLastCalledWith(emptyFilters, 'cursor-2', 10)
    expect(result.current.page).toBe(2)

    await act(async () => {
      await result.current.previousPage()
    })

    await waitFor(() => expect(result.current.items).toEqual([itemA]))
    expect(loadPage).toHaveBeenLastCalledWith(emptyFilters, undefined, 10)
    expect(result.current.page).toBe(1)
  })

  it('resets to the first page when page size changes', async () => {
    loadPage
      .mockResolvedValueOnce({ items: [itemA], next_token: 'cursor-2', has_more: true })
      .mockResolvedValueOnce({ items: [itemA, itemB], next_token: null, has_more: false })

    const { result } = renderHook(() => useCursorPagedList(emptyFilters, loadPage))
    await waitFor(() => expect(result.current.items).toEqual([itemA]))

    await act(async () => {
      await result.current.setPageSize(25)
    })

    await waitFor(() => expect(result.current.items).toEqual([itemA, itemB]))
    expect(loadPage).toHaveBeenLastCalledWith(emptyFilters, undefined, 25)
    expect(result.current.page).toBe(1)
    expect(result.current.pageSize).toBe(25)
  })

  it('derives totalPages from the backend total when present', async () => {
    loadPage.mockResolvedValueOnce({
      items: [itemA],
      next_token: 'cursor-2',
      has_more: true,
      total: 25,
    })

    const { result } = renderHook(() => useCursorPagedList(emptyFilters, loadPage))

    await waitFor(() => expect(result.current.totalItems).toBe(25))
    expect(result.current.totalPages).toBe(3)
  })

  it('leaves totalPages null when the backend omits total (e.g. free-text search active)', async () => {
    loadPage.mockResolvedValueOnce({ items: [itemA], next_token: null, has_more: false })

    const { result } = renderHook(() => useCursorPagedList(emptyFilters, loadPage))

    await waitFor(() => expect(result.current.items).toEqual([itemA]))
    expect(result.current.totalItems).toBeNull()
    expect(result.current.totalPages).toBeNull()
  })
})
