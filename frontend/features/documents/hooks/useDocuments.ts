import { usePaginatedList } from '@/lib/hooks/usePaginatedList'
import { documentsApi } from '../api'
import type { DocumentListFilters } from '../types'

export function useDocuments(filters: DocumentListFilters) {
  const { items, ...state } = usePaginatedList(filters, documentsApi.list)
  return { ...state, documents: items }
}
