import { useCursorPagedList } from '@/lib/hooks/useCursorPagedList'
import { documentsApi } from '../api'
import type { DocumentListFilters } from '../types'

export function useDocuments(filters: DocumentListFilters) {
  const { items, ...state } = useCursorPagedList(filters, documentsApi.list)
  return { ...state, documents: items }
}
