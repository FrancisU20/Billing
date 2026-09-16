import { useCallback } from 'react'
import type { PageSize } from '@/constants/pagination'
import { useEagerPagedList } from '@/lib/hooks/useEagerPagedList'
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
  const loadPage = useCallback(
    (f: PlanListFilters, nextToken: string | undefined, limit: PageSize) =>
      plansApi.adminListPage(f, nextToken, limit).then((res) => ({
        ...res,
        items: sortByOrder(res.items),
      })),
    [],
  )

  const { pageItems, allItems, ...state } = useEagerPagedList(filters, loadPage)
  return { plans: pageItems, allPlans: allItems, ...state }
}
