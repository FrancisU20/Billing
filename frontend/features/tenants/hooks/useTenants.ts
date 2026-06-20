import { useCursorPagedList } from '@/lib/hooks/useCursorPagedList'
import { tenantsApi } from '../api'
import type { TenantListFilters } from '../types'

export function useTenants(filters: TenantListFilters = {}) {
  const { items, ...state } = useCursorPagedList(filters, tenantsApi.list)
  return { ...state, tenants: items }
}
