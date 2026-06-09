import { useCallback, useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { plansApi } from '../api'
import type { Plan, PlanListFilters } from '../types'

interface PlansState {
  plans: Plan[]
  loading: boolean
  error: ApiError | null
}

export function usePlans() {
  const [state, setState] = useState<PlansState>({ plans: [], loading: true, error: null })

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const res = await plansApi.list()
      const sorted = [...res.items].sort((a, b) => a.order - b.order)
      setState({ plans: sorted, loading: false, error: null })
    } catch (e) {
      setState({ plans: [], loading: false, error: toApiError(e) })
    }
  }, [])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { ...state, refresh: fetch }
}

export function useAdminPlans(filters: PlanListFilters = {}) {
  const [state, setState] = useState<PlansState>({ plans: [], loading: true, error: null })

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const res = await plansApi.adminList(filters)
      const sorted = [...res.items].sort((a, b) => a.order - b.order)
      setState({ plans: sorted, loading: false, error: null })
    } catch (e) {
      setState({ plans: [], loading: false, error: toApiError(e) })
    }
  }, [filters])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { ...state, refresh: fetch }
}
