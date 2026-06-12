import { useCallback, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'

/**
 * Envuelve una acción async (crear/actualizar/cambiar estado) con los estados
 * `submitting`/`error` y el manejo try/catch/finally + `toApiError` estándar.
 */
export function useFormSubmit<TArgs extends unknown[]>(action: (...args: TArgs) => Promise<void>) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const submit = useCallback(
    async (...args: TArgs) => {
      setSubmitting(true)
      setError(null)
      try {
        await action(...args)
      } catch (e) {
        setError(toApiError(e))
      } finally {
        setSubmitting(false)
      }
    },
    [action],
  )

  return { submitting, error, submit }
}
