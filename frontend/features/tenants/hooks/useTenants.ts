import { usePaginatedList } from '@/lib/hooks/usePaginatedList'
import { tenantsApi } from '../api'
import type { TenantListFilters } from '../types'

export function useTenants(filters: TenantListFilters = {}) {
  const { items, ...state } = usePaginatedList(filters, tenantsApi.list)
  return { ...state, tenants: items }
}
