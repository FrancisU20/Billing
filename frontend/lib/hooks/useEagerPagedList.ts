import { useCallback, useEffect, useRef, useState } from 'react'
import { type PageSize } from '@/constants/pagination'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useLocalPagedItems } from '@/lib/hooks/useLocalPagedItems'
import type { CursorPagedListResponse } from '@/lib/hooks/useCursorPagedList'

/** Internal fetch chunk size while sweeping all matching pages — independent from the
 * user-facing page size selector (10/25/50). Matches the backend's own cap. */
const SWEEP_PAGE_SIZE: PageSize = 50

/** Safety cap on how many items this hook will hold in memory for local pagination.
 * At SWEEP_PAGE_SIZE=50 this is 20 sequential round-trips — past this, `truncated`
 * is set and the caller should ask the user to narrow the filter instead of silently
 * loading an unbounded amount of data. */
const MAX_SWEPT_PAGES = 20

type EagerPageLoader<T, F> = (
  filters: F,
  nextToken: string | undefined,
  limit: PageSize,
) => Promise<CursorPagedListResponse<T>>

/**
 * Loads every item matching `filters` by walking the existing cursor-paginated endpoint
 * sequentially (cursors are dependent, can't be parallelized), then paginates the result
 * locally with real page-jump support (`goToPage`). Intended for tenant-scoped catalogs
 * bounded in practice (clients, products) — NOT for domains that grow unbounded over time
 * (documents), where this would eventually load too much data.
 */
export function useEagerPagedList<T, F>(
  filters: F,
  loadPage: EagerPageLoader<T, F>,
  initialPageSize: PageSize = 10,
) {
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)
  const [truncated, setTruncated] = useState(false)
  const [backendTotal, setBackendTotal] = useState<number | null>(null)
  const requestIdRef = useRef(0)

  const sweep = useCallback(async () => {
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    setLoading(true)
    setError(null)

    try {
      let cursor: string | undefined
      let collected: T[] = []
      let total: number | null = null
      let hasMore = true
      let pages = 0

      while (hasMore && pages < MAX_SWEPT_PAGES) {
        const res = await loadPage(filters, cursor, SWEEP_PAGE_SIZE)
        if (requestId !== requestIdRef.current) return
        collected = collected.concat(res.items)
        total = res.total ?? total
        hasMore = res.has_more
        cursor = res.next_token ?? undefined
        pages += 1
      }

      if (requestId !== requestIdRef.current) return
      setItems(collected)
      setTruncated(hasMore)
      setBackendTotal(total)
      setLoading(false)
    } catch (e) {
      if (requestId !== requestIdRef.current) return
      setError(toApiError(e))
      setLoading(false)
    }
  }, [filters, loadPage])

  useEffect(() => {
    void sweep()
  }, [sweep])

  const local = useLocalPagedItems(items, initialPageSize)

  return {
    ...local,
    loading,
    error,
    truncated,
    backendTotal,
    refresh: sweep,
  }
}
