import { useCallback, useEffect, useRef, useState } from 'react'
import { DEFAULT_PAGE_SIZE, type PageSize } from '@/constants/pagination'
import { toApiError, type ApiError } from '@/lib/api/errors'

export interface CursorPagedListResponse<T> {
  items: T[]
  next_token: string | null
  has_more: boolean
  total?: number | null
}

interface CursorPagedListState<T> {
  items: T[]
  nextToken: string | null
  hasMore: boolean
  total: number | null
  page: number
  pageSize: PageSize
  loading: boolean
  error: ApiError | null
}

type CursorPageLoader<T, F> = (
  filters: F,
  nextToken: string | undefined,
  limit: PageSize,
) => Promise<CursorPagedListResponse<T>>

export function useCursorPagedList<T, F>(
  filters: F,
  loadPage: CursorPageLoader<T, F>,
  initialPageSize: PageSize = DEFAULT_PAGE_SIZE,
) {
  const initialState: CursorPagedListState<T> = {
    items: [],
    nextToken: null,
    hasMore: false,
    total: null,
    page: 1,
    pageSize: initialPageSize,
    loading: true,
    error: null,
  }
  const [state, setState] = useState<CursorPagedListState<T>>(initialState)
  const stateRef = useRef(state)
  const pageTokensRef = useRef<Array<string | undefined>>([undefined])
  const requestIdRef = useRef(0)

  const setSyncedState = useCallback((next: CursorPagedListState<T>) => {
    stateRef.current = next
    setState(next)
  }, [])

  const load = useCallback(
    async (page: number, pageSize: PageSize, tokens: Array<string | undefined>) => {
      const requestId = requestIdRef.current + 1
      requestIdRef.current = requestId
      setSyncedState({ ...stateRef.current, page, pageSize, loading: true, error: null })

      try {
        const res = await loadPage(filters, tokens[page - 1], pageSize)
        if (requestId !== requestIdRef.current) return
        setSyncedState({
          items: res.items,
          nextToken: res.next_token,
          hasMore: res.has_more,
          total: res.total ?? null,
          page,
          pageSize,
          loading: false,
          error: null,
        })
      } catch (e) {
        if (requestId !== requestIdRef.current) return
        setSyncedState({
          ...stateRef.current,
          page,
          pageSize,
          loading: false,
          error: toApiError(e),
        })
      }
    },
    [filters, loadPage, setSyncedState],
  )

  const refresh = useCallback(async () => {
    pageTokensRef.current = [undefined]
    await load(1, stateRef.current.pageSize, pageTokensRef.current)
  }, [load])

  const nextPage = useCallback(async () => {
    const snapshot = stateRef.current
    if (snapshot.loading || !snapshot.hasMore || !snapshot.nextToken) return
    const nextPageNumber = snapshot.page + 1
    const nextTokens = [...pageTokensRef.current]
    nextTokens[nextPageNumber - 1] = snapshot.nextToken
    pageTokensRef.current = nextTokens
    await load(nextPageNumber, snapshot.pageSize, nextTokens)
  }, [load])

  const previousPage = useCallback(async () => {
    const snapshot = stateRef.current
    if (snapshot.loading || snapshot.page <= 1) return
    await load(snapshot.page - 1, snapshot.pageSize, pageTokensRef.current)
  }, [load])

  const setPageSize = useCallback(
    async (pageSize: PageSize) => {
      pageTokensRef.current = [undefined]
      await load(1, pageSize, pageTokensRef.current)
    },
    [load],
  )

  useEffect(() => {
    pageTokensRef.current = [undefined]
    void load(1, stateRef.current.pageSize, pageTokensRef.current)
  }, [load])

  return {
    ...state,
    totalItems: state.total,
    totalPages: state.total != null ? Math.max(1, Math.ceil(state.total / state.pageSize)) : null,
    canGoNext: state.hasMore,
    canGoPrevious: state.page > 1,
    refresh,
    nextPage,
    previousPage,
    setPageSize,
  }
}
