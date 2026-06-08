import { useCallback, useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { tenantsApi } from '../api'
import type { Tenant } from '../types'

interface TenantsState {
  tenants: Tenant[]
  nextToken: string | null
  hasMore: boolean
  loading: boolean
  loadingMore: boolean
  error: ApiError | null
}

export function useTenants() {
  const [state, setState] = useState<TenantsState>({
    tenants: [],
    nextToken: null,
    hasMore: false,
    loading: true,
    loadingMore: false,
    error: null,
  })

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const res = await tenantsApi.list()
      setState({
        tenants: res.items,
        nextToken: res.next_token,
        hasMore: res.has_more,
        loading: false,
        loadingMore: false,
        error: null,
      })
    } catch (e) {
      setState((s) => ({ ...s, loading: false, error: toApiError(e) }))
    }
  }, [])

  const fetchMore = useCallback(async () => {
    if (!state.hasMore || state.loadingMore || !state.nextToken) return
    setState((s) => ({ ...s, loadingMore: true }))
    try {
      const res = await tenantsApi.list(state.nextToken!)
      setState((s) => ({
        ...s,
        tenants: [...s.tenants, ...res.items],
        nextToken: res.next_token,
        hasMore: res.has_more,
        loadingMore: false,
      }))
    } catch (e) {
      setState((s) => ({ ...s, loadingMore: false, error: toApiError(e) }))
    }
  }, [state.hasMore, state.loadingMore, state.nextToken])

  useEffect(() => { fetch() }, [fetch])

  return { ...state, refresh: fetch, fetchMore }
}
