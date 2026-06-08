import { useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { tenantsApi } from '../api'
import type { Tenant } from '../types'

export function useTenant(id: string | null) {
  const [tenant, setTenant] = useState<Tenant | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    tenantsApi
      .getById(id)
      .then(setTenant)
      .catch((e) => setError(toApiError(e)))
      .finally(() => setLoading(false))
  }, [id])

  return { tenant, loading, error }
}
