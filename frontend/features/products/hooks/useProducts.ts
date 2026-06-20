import { useCursorPagedList } from '@/lib/hooks/useCursorPagedList'
import { productsApi } from '../api'
import type { ProductListFilters } from '../types'

export function useProducts(filters: ProductListFilters) {
  const { items, ...state } = useCursorPagedList(filters, productsApi.list)
  return { ...state, products: items }
}
