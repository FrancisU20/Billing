import { usePaginatedList } from '@/lib/hooks/usePaginatedList'
import { clientsApi } from '../api'
import type { ClientListFilters } from '../types'

export function useClients(filters: ClientListFilters) {
  const { items, ...state } = usePaginatedList(filters, clientsApi.list)
  return { ...state, clients: items }
}
