import { useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { clientsApi } from '../api'
import type { Client } from '../types'

export function useClient(id: string | null) {
  const [client, setClient] = useState<Client | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    if (!id) {
      setClient(null)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    clientsApi
      .getById(id)
      .then((data) => {
        if (!cancelled) setClient(data)
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
  }, [id])

  return { client, loading, error }
}
