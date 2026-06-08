import { useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { plansApi } from '../api'
import type { Plan } from '../types'

export function usePlan(slug: string | null) {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    if (!slug) {
      setPlan(null)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    plansApi
      .getBySlug(slug)
      .then((data) => {
        if (!cancelled) setPlan(data)
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
  }, [slug])

  return { plan, loading, error }
}
