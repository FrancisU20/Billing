import { useCallback, useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { clientsApi } from '../api'
import type { Client, ClientListFilters } from '../types'

interface ClientsState {
  clients: Client[]
  nextToken: string | null
  hasMore: boolean
  loading: boolean
  loadingMore: boolean
  error: ApiError | null
}

export function useClients(filters: ClientListFilters) {
  const [state, setState] = useState<ClientsState>({
    clients: [],
    nextToken: null,
    hasMore: false,
    loading: true,
    loadingMore: false,
    error: null,
  })

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const res = await clientsApi.list(filters)
      setState({
        clients: res.items,
        nextToken: res.next_token,
        hasMore: res.has_more,
        loading: false,
        loadingMore: false,
        error: null,
      })
    } catch (e) {
      setState((s) => ({ ...s, loading: false, loadingMore: false, error: toApiError(e) }))
    }
  }, [filters])

  const fetchMore = useCallback(async () => {
    const { hasMore, loadingMore, nextToken } = state
    if (!hasMore || loadingMore || !nextToken) return
    setState((s) => ({ ...s, loadingMore: true }))
    try {
      const res = await clientsApi.list(filters, nextToken)
      setState((s) => ({
        ...s,
        clients: [...s.clients, ...res.items],
        nextToken: res.next_token,
        hasMore: res.has_more,
        loadingMore: false,
      }))
    } catch (e) {
      setState((s) => ({ ...s, loadingMore: false, error: toApiError(e) }))
    }
  }, [filters, state])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { ...state, refresh: fetch, fetchMore }
}
