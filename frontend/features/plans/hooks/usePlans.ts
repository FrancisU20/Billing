import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { plansApi } from '../api'
import type { Plan, PlanListFilters } from '../types'

function sortByOrder(plans: Plan[]) {
  return [...plans].sort((a, b) => a.order - b.order)
}

export function usePlans() {
  const fetcher = useCallback(async () => {
    const res = await plansApi.list()
    return sortByOrder(res.items)
  }, [])
  const { data, loading, error, refresh } = useFetch(fetcher)

  return { plans: data ?? [], loading, error, refresh }
}

export function useAdminPlans(filters: PlanListFilters = {}) {
  const fetcher = useCallback(async () => {
    const res = await plansApi.adminList(filters)
    return sortByOrder(res.items)
  }, [filters])
  const { data, loading, error, refresh } = useFetch(fetcher)

  return { plans: data ?? [], loading, error, refresh }
}
