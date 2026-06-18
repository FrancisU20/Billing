import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { productsApi } from '../api'

export function useProduct(id: string | null) {
  const fetcher = useCallback(() => productsApi.getById(id as string), [id])
  const { data, loading, error, refresh } = useFetch(id ? fetcher : null)
  return { product: data, loading, error, refresh }
}
