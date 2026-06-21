import { useEagerPagedList } from '@/lib/hooks/useEagerPagedList'
import { tenantsApi } from '../api'
import type { TenantListFilters } from '../types'

export function useTenants(filters: TenantListFilters = {}) {
  const { pageItems, ...state } = useEagerPagedList(filters, tenantsApi.list)
  return { ...state, tenants: pageItems }
}
