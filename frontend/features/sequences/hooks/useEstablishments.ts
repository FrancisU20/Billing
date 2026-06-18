import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { sequencesApi } from '../api'

export function useEstablishments(tenantId: string | null) {
  const fetcher = useCallback(() => sequencesApi.list(tenantId as string), [tenantId])
  const { data, loading, error, refresh } = useFetch(tenantId ? fetcher : null)

  return { establishments: data?.items ?? [], loading, error, refresh }
}
