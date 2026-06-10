import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { tenantsApi } from '../api'

export function useTenant(id: string | null) {
  const fetcher = useCallback(() => tenantsApi.getById(id as string), [id])
  const { data, loading, error, refresh } = useFetch(id ? fetcher : null)

  return { tenant: data, loading, error, refresh }
}
