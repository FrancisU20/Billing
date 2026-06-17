import { useEffect, useState } from 'react'
import { plansApi } from '@/features/plans/api'
import type { Plan } from '@/features/plans/schemas'

export function usePlan(planId: string | null | undefined) {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!planId) return
    setLoading(true)
    plansApi
      .list()
      .then((data) => {
        setPlan(data.items.find((p) => p.id === planId) ?? null)
      })
      .catch(() => setPlan(null))
      .finally(() => setLoading(false))
  }, [planId])

  return { plan, loading }
}
