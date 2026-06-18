import { useCallback, useEffect } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { documentsApi } from '../api'

const POLL_INTERVAL_MS = 5000
const POLLING_STATUSES = new Set(['PENDING', 'PROCESSING'])

/**
 * La autorización del SRI es asíncrona (segundos a minutos, ver
 * `invoice_processor` en el backend). Mientras el documento esté
 * PENDING/PROCESSING, se refresca solo cada 5s — sin esto el usuario vería el
 * estado congelado y pensaría que algo falló.
 */
export function useDocument(id: string | null) {
  const fetcher = useCallback(() => documentsApi.getById(id as string), [id])
  const { data, loading, error, refresh } = useFetch(id ? fetcher : null)

  useEffect(() => {
    if (!data || !POLLING_STATUSES.has(data.status)) return
    const interval = setInterval(refresh, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [data, refresh])

  return { document: data, loading, error, refresh }
}
