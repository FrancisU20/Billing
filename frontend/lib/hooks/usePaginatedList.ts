import { useCallback, useEffect, useRef, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'

export interface PaginatedListResponse<T> {
  items: T[]
  next_token: string | null
  has_more: boolean
}

interface PaginatedListState<T> {
  items: T[]
  nextToken: string | null
  hasMore: boolean
  loading: boolean
  loadingMore: boolean
  error: ApiError | null
}

export function usePaginatedList<T, F>(
  filters: F,
  loadPage: (filters: F, nextToken?: string) => Promise<PaginatedListResponse<T>>,
) {
  const initialState: PaginatedListState<T> = {
    items: [],
    nextToken: null,
    hasMore: false,
    loading: true,
    loadingMore: false,
    error: null,
  }
  const [state, setState] = useState<PaginatedListState<T>>(initialState)
  const stateRef = useRef(state)
  const loadingMoreRef = useRef(false)
  const requestIdRef = useRef(0)

  const setSyncedState = useCallback((next: PaginatedListState<T>) => {
    stateRef.current = next
    setState(next)
  }, [])

  const refresh = useCallback(async () => {
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    loadingMoreRef.current = false
    setSyncedState({ ...stateRef.current, loading: true, loadingMore: false, error: null })
    try {
      const res = await loadPage(filters)
      if (requestId !== requestIdRef.current) return
      setSyncedState({
        items: res.items,
        nextToken: res.next_token,
        hasMore: res.has_more,
        loading: false,
        loadingMore: false,
        error: null,
      })
    } catch (e) {
      if (requestId !== requestIdRef.current) return
      setSyncedState({
        ...stateRef.current,
        loading: false,
        loadingMore: false,
        error: toApiError(e),
      })
    }
  }, [filters, loadPage, setSyncedState])

  const fetchMore = useCallback(async () => {
    if (loadingMoreRef.current) return

    const snapshot = stateRef.current
    if (snapshot.loading || !snapshot.hasMore || snapshot.loadingMore || !snapshot.nextToken) return

    const token = snapshot.nextToken
    loadingMoreRef.current = true
    setSyncedState({ ...snapshot, loadingMore: true, error: null })
    const requestId = requestIdRef.current

    try {
      const res = await loadPage(filters, token)
      if (requestId !== requestIdRef.current) return
      setSyncedState({
        ...stateRef.current,
        items: [...stateRef.current.items, ...res.items],
        nextToken: res.next_token,
        hasMore: res.has_more,
        loadingMore: false,
      })
    } catch (e) {
      if (requestId !== requestIdRef.current) return
      setSyncedState({ ...stateRef.current, loadingMore: false, error: toApiError(e) })
    } finally {
      if (requestId === requestIdRef.current) {
        loadingMoreRef.current = false
      }
    }
  }, [filters, loadPage, setSyncedState])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { ...state, refresh, fetchMore }
}
