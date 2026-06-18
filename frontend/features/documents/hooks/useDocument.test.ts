// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Document } from '../types'

const getById = vi.fn()
vi.mock('../api', () => ({
  documentsApi: { getById: (...args: unknown[]) => getById(...args) },
}))

import { useDocument } from './useDocument'

const pendingDocument = { document_id: 'doc-1', status: 'PENDING' } as unknown as Document
const authorizedDocument = { document_id: 'doc-1', status: 'AUTHORIZED' } as unknown as Document

beforeEach(() => {
  getById.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useDocument', () => {
  it('does not fetch when id is null', () => {
    const { result } = renderHook(() => useDocument(null))
    expect(result.current.loading).toBe(false)
    expect(result.current.document).toBeNull()
    expect(getById).not.toHaveBeenCalled()
  })

  it('loads the document by id', async () => {
    getById.mockResolvedValueOnce(authorizedDocument)
    const { result } = renderHook(() => useDocument('doc-1'))
    await waitFor(() => expect(result.current.document).toEqual(authorizedDocument))
    expect(getById).toHaveBeenCalledWith('doc-1')
  })

  it('polls every 5s while the document is PENDING or PROCESSING', async () => {
    vi.useFakeTimers()
    getById.mockResolvedValueOnce(pendingDocument)
    const { result } = renderHook(() => useDocument('doc-1'))
    await act(async () => {
      await vi.runOnlyPendingTimersAsync()
    })
    expect(result.current.document).toEqual(pendingDocument)

    getById.mockResolvedValueOnce(pendingDocument)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(getById).toHaveBeenCalledTimes(2)

    getById.mockResolvedValueOnce(authorizedDocument)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
    expect(result.current.document).toEqual(authorizedDocument)
    expect(getById).toHaveBeenCalledTimes(3)

    // Ya autorizado — no debe seguir haciendo poll.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000)
    })
    expect(getById).toHaveBeenCalledTimes(3)
  })
})
