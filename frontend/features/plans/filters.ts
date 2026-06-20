import {
  PLAN_LIMIT_CYCLE_OPTIONS,
  PLAN_STATUS_OPTIONS,
  type PlanSearchMode,
  type PlanStatusFilter,
} from './constants'
import { formatDateRangeLabel } from '@/lib/utils/format'
import type { LimitCycle, PlanListFilters } from './types'

export interface PlanFilterDraft {
  searchMode: PlanSearchMode
  search: string
  status: PlanStatusFilter
  limitCycle: LimitCycle | 'all'
  createdFrom: string
  createdTo: string
}

export const emptyPlanFilterDraft: PlanFilterDraft = {
  searchMode: 'q',
  search: '',
  status: 'all',
  limitCycle: 'all',
  createdFrom: '',
  createdTo: '',
}

export function toPlanListFilters(value: PlanFilterDraft): PlanListFilters {
  const search = value.search.trim()
  return {
    q: value.searchMode === 'q' && search.length >= 3 ? search : undefined,
    slug: value.searchMode === 'slug' && search.length >= 3 ? search : undefined,
    status: value.status === 'all' ? undefined : value.status,
    limit_cycle: value.limitCycle === 'all' ? undefined : value.limitCycle,
    created_from: value.createdFrom.trim() || undefined,
    created_to: value.createdTo.trim() || undefined,
  }
}

export interface PlanFilterChip {
  key: 'status' | 'limitCycle' | 'created'
  label: string
}

export function planFilterChips(value: PlanFilterDraft): PlanFilterChip[] {
  const chips: PlanFilterChip[] = []
  if (value.status !== 'all') {
    const option = PLAN_STATUS_OPTIONS.find((item) => item.value === value.status)
    chips.push({ key: 'status', label: `Estado: ${option?.label ?? value.status}` })
  }
  if (value.limitCycle !== 'all') {
    const option = PLAN_LIMIT_CYCLE_OPTIONS.find((item) => item.value === value.limitCycle)
    chips.push({ key: 'limitCycle', label: `Ciclo: ${option?.label ?? value.limitCycle}` })
  }
  if (value.createdFrom || value.createdTo) {
    chips.push({
      key: 'created',
      label: `Creación: ${formatDateRangeLabel(value.createdFrom, value.createdTo)}`,
    })
  }
  return chips
}

export function clearPlanFilterField(
  value: PlanFilterDraft,
  key: PlanFilterChip['key'],
): PlanFilterDraft {
  switch (key) {
    case 'status':
      return { ...value, status: 'all' }
    case 'limitCycle':
      return { ...value, limitCycle: 'all' }
    case 'created':
      return { ...value, createdFrom: '', createdTo: '' }
  }
}
