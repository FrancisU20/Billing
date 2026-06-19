import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { productsApi } from '../api'

export function useDiscountCampaign() {
  const fetcher = useCallback(() => productsApi.getDiscountCampaign(), [])
  const { data, loading, error, refresh } = useFetch(fetcher)

  return { campaign: data, loading, error, refresh }
}
