import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { tenantsApi } from '../api'

export function useSuperadminDashboard() {
  const fetcher = useCallback(() => tenantsApi.dashboardSummary(), [])
  const { data, ...state } = useFetch(fetcher)
  return { summary: data, ...state }
}
