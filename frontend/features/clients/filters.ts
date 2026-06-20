import { formatDateRangeLabel } from '@/lib/utils/format'
import {
  CLIENT_IDENTIFICATION_LABELS,
  CLIENT_STATUS_LABELS,
  type ClientSearchMode,
} from '@/features/clients/constants'
import type { ClientListFilters, ClientStatus, IdentificationType } from './types'

export interface ClientFilterDraft {
  searchMode: ClientSearchMode
  search: string
  status: ClientStatus | 'all'
  identificationType: IdentificationType | 'all'
  createdFrom: string
  createdTo: string
}

export const emptyClientFilterDraft: ClientFilterDraft = {
  searchMode: 'q',
  search: '',
  status: 'all',
  identificationType: 'all',
  createdFrom: '',
  createdTo: '',
}

export function toClientListFilters(value: ClientFilterDraft): ClientListFilters {
  const search = value.search.trim()
  return {
    q: value.searchMode === 'q' && search.length >= 3 ? search : undefined,
    identification:
      value.searchMode === 'identification' && search.length >= 3 ? search : undefined,
    status: value.status === 'all' ? undefined : value.status,
    identification_type: value.identificationType === 'all' ? undefined : value.identificationType,
    created_from: value.createdFrom.trim() || undefined,
    created_to: value.createdTo.trim() || undefined,
  }
}

export interface ClientFilterChip {
  key: 'status' | 'identificationType' | 'created'
  label: string
}

export function clientFilterChips(value: ClientFilterDraft): ClientFilterChip[] {
  const chips: ClientFilterChip[] = []
  if (value.status !== 'all') {
    chips.push({ key: 'status', label: `Estado: ${CLIENT_STATUS_LABELS[value.status]}` })
  }
  if (value.identificationType !== 'all') {
    chips.push({
      key: 'identificationType',
      label: `Tipo: ${CLIENT_IDENTIFICATION_LABELS[value.identificationType]}`,
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

export function clearClientFilterField(
  value: ClientFilterDraft,
  key: ClientFilterChip['key'],
): ClientFilterDraft {
  switch (key) {
    case 'status':
      return { ...value, status: 'all' }
    case 'identificationType':
      return { ...value, identificationType: 'all' }
    case 'created':
      return { ...value, createdFrom: '', createdTo: '' }
  }
}
