import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { clientsApi } from '../api'

export function useClient(id: string | null) {
  const fetcher = useCallback(() => clientsApi.getById(id as string), [id])
  const { data, loading, error, refresh } = useFetch(id ? fetcher : null)

  return { client: data, loading, error, refresh }
}
