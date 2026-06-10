import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { plansApi } from '../api'
import type { Plan } from '../types'

function usePlanBase(fetcher: (slug: string) => Promise<Plan>, slug: string | null) {
  const fetch = useCallback(() => fetcher(slug as string), [fetcher, slug])
  const { data, loading, error, refresh } = useFetch(slug ? fetch : null)

  return { plan: data, loading, error, refresh }
}

export function usePlan(slug: string | null) {
  return usePlanBase(plansApi.getBySlug, slug)
}

export function useAdminPlan(slug: string | null) {
  return usePlanBase(plansApi.adminGetBySlug, slug)
}
