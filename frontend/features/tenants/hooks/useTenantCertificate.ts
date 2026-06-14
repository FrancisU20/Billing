import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { tenantsApi } from '../api'

export function useTenantCertificate(tenantId: string | null) {
  const fetcher = useCallback(() => tenantsApi.getCertificate(tenantId as string), [tenantId])
  const { data, loading, error, refresh } = useFetch(tenantId ? fetcher : null)

  return { certificate: data, loading, error, refresh }
}
