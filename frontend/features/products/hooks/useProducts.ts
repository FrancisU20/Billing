import { usePaginatedList } from '@/lib/hooks/usePaginatedList'
import { productsApi } from '../api'
import type { ProductListFilters } from '../types'

export function useProducts(filters: ProductListFilters) {
  const { items, ...state } = usePaginatedList(filters, productsApi.list)
  return { ...state, products: items }
}
