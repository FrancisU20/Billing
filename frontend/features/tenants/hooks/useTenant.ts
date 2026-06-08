import { useCallback, useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { tenantsApi } from '../api'
import type { Tenant } from '../types'

export function useTenant(id: string | null) {
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [refreshCount, setRefreshCount] = useState(0)

  const refresh = useCallback(() => setRefreshCount((c) => c + 1), [])

  useEffect(() => {
    if (!id) {
      setTenant(null)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    tenantsApi
      .getById(id)
      .then((data) => {
        if (!cancelled) setTenant(data)
      })
      .catch((e) => {
        if (!cancelled) setError(toApiError(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [id, refreshCount])

  return { tenant, loading, error, refresh }
}
