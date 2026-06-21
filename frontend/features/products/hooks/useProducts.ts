import { useEagerPagedList } from '@/lib/hooks/useEagerPagedList'
import { productsApi } from '../api'
import type { ProductListFilters } from '../types'

export function useProducts(filters: ProductListFilters) {
  const { pageItems, ...state } = useEagerPagedList(filters, productsApi.list)
  return { ...state, products: pageItems }
}
