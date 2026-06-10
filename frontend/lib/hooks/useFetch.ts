import { useCallback, useEffect, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'

interface FetchState<T> {
  data: T | null
  loading: boolean
  error: ApiError | null
}

/**
 * Carga un único recurso. `fetcher` debe ser estable (useCallback) y memoizado
 * con sus propias dependencias; pasar `null` para no ejecutar el fetch (ej.
 * mientras un id requerido todavía no está disponible).
 */
export function useFetch<T>(fetcher: (() => Promise<T>) | null) {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    loading: fetcher !== null,
    error: null,
  })
  const [refreshCount, setRefreshCount] = useState(0)

  const refresh = useCallback(() => setRefreshCount((c) => c + 1), [])

  useEffect(() => {
    if (!fetcher) {
      setState({ data: null, loading: false, error: null })
      return
    }

    let cancelled = false
    setState((s) => ({ ...s, loading: true, error: null }))

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null })
      })
      .catch((e) => {
        if (!cancelled) setState({ data: null, loading: false, error: toApiError(e) })
      })

    return () => {
      cancelled = true
    }
  }, [fetcher, refreshCount])

  return { ...state, refresh }
}
