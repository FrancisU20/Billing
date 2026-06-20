import { useCursorPagedList } from '@/lib/hooks/useCursorPagedList'
import { clientsApi } from '../api'
import type { ClientListFilters } from '../types'

export function useClients(filters: ClientListFilters) {
  const { items, ...state } = useCursorPagedList(filters, clientsApi.list)
  return { ...state, clients: items }
}
