import { useEagerPagedList } from '@/lib/hooks/useEagerPagedList'
import { clientsApi } from '../api'
import type { ClientListFilters } from '../types'

export function useClients(filters: ClientListFilters) {
  const { pageItems, ...state } = useEagerPagedList(filters, clientsApi.list)
  return { ...state, clients: pageItems }
}
