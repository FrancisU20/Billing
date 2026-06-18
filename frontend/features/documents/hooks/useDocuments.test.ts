// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Document } from '../types'

const list = vi.fn()
vi.mock('../api', () => ({
  documentsApi: { list: (...args: unknown[]) => list(...args) },
}))

import { useDocuments } from './useDocuments'

const documentA = { document_id: 'doc-a' } as unknown as Document

beforeEach(() => {
  list.mockReset()
})

describe('useDocuments', () => {
  it('loads documents for the given filters', async () => {
    list.mockResolvedValueOnce({ items: [documentA], next_token: null, has_more: false })
    const filters = { status: 'PENDING' as const }
    const { result } = renderHook(() => useDocuments(filters))

    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.documents).toEqual([documentA]))
    expect(list).toHaveBeenCalledWith(filters)
  })
})
