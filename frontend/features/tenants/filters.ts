import { formatDateRangeLabel } from '@/lib/utils/format'
import {
  TENANT_ENVIRONMENT_LABELS,
  TENANT_PLAN_STATUS_LABELS,
  TENANT_STATUS_LABELS,
  type TenantSearchMode,
} from './constants'
import type { PlanStatus, SriEnvironment, TenantListFilters, TenantStatus } from './types'

export interface TenantFilterDraft {
  searchMode: TenantSearchMode
  search: string
  status: TenantStatus | 'all'
  sriEnvironment: SriEnvironment | 'all'
  planStatus: PlanStatus | 'all'
  createdFrom: string
  createdTo: string
}

export const emptyTenantFilterDraft: TenantFilterDraft = {
  searchMode: 'q',
  search: '',
  status: 'all',
  sriEnvironment: 'all',
  planStatus: 'all',
  createdFrom: '',
  createdTo: '',
}

export function toTenantListFilters(value: TenantFilterDraft): TenantListFilters {
  const search = value.search.trim()
  return {
    q: value.searchMode === 'q' && search.length >= 3 ? search : undefined,
    ruc: value.searchMode === 'ruc' && search.length >= 3 ? search : undefined,
    status: value.status === 'all' ? undefined : value.status,
    sri_environment: value.sriEnvironment === 'all' ? undefined : value.sriEnvironment,
    plan_status: value.planStatus === 'all' ? undefined : value.planStatus,
    created_from: value.createdFrom.trim() || undefined,
    created_to: value.createdTo.trim() || undefined,
  }
}

export interface TenantFilterChip {
  key: 'status' | 'sriEnvironment' | 'planStatus' | 'created'
  label: string
}

export function tenantFilterChips(value: TenantFilterDraft): TenantFilterChip[] {
  const chips: TenantFilterChip[] = []
  if (value.status !== 'all') {
    chips.push({ key: 'status', label: `Estado: ${TENANT_STATUS_LABELS[value.status]}` })
  }
  if (value.sriEnvironment !== 'all') {
    chips.push({
      key: 'sriEnvironment',
      label: `Entorno: ${TENANT_ENVIRONMENT_LABELS[value.sriEnvironment]}`,
    })
  }
  if (value.planStatus !== 'all') {
    chips.push({
      key: 'planStatus',
      label: `Plan: ${TENANT_PLAN_STATUS_LABELS[value.planStatus]}`,
    })
  }
  if (value.createdFrom || value.createdTo) {
    chips.push({
      key: 'created',
      label: `Creación: ${formatDateRangeLabel(value.createdFrom, value.createdTo)}`,
    })
  }
  return chips
}

export function clearTenantFilterField(
  value: TenantFilterDraft,
  key: TenantFilterChip['key'],
): TenantFilterDraft {
  switch (key) {
    case 'status':
      return { ...value, status: 'all' }
    case 'sriEnvironment':
      return { ...value, sriEnvironment: 'all' }
    case 'planStatus':
      return { ...value, planStatus: 'all' }
    case 'created':
      return { ...value, createdFrom: '', createdTo: '' }
  }
}
