import { formatDateRangeLabel } from '@/lib/utils/format'
import { DOCUMENT_STATUS_LABELS } from './constants'
import type { DocumentListFilters, DocumentStatus } from './types'

export interface DocumentFilterDraft {
  status: DocumentStatus | 'all'
  serie: string
  dateFrom: string
  dateTo: string
}

export const emptyDocumentFilterDraft: DocumentFilterDraft = {
  status: 'all',
  serie: '',
  dateFrom: '',
  dateTo: '',
}

export function toDocumentListFilters(value: DocumentFilterDraft): DocumentListFilters {
  const serie = value.serie.trim()
  return {
    status: value.status === 'all' ? undefined : value.status,
    serie: serie.length >= 3 ? serie : undefined,
    date_from: value.dateFrom.trim() || undefined,
    date_to: value.dateTo.trim() || undefined,
  }
}

export interface DocumentFilterChip {
  key: 'status' | 'date'
  label: string
}

export function documentFilterChips(value: DocumentFilterDraft): DocumentFilterChip[] {
  const chips: DocumentFilterChip[] = []
  if (value.status !== 'all') {
    chips.push({ key: 'status', label: `Estado: ${DOCUMENT_STATUS_LABELS[value.status]}` })
  }
  if (value.dateFrom || value.dateTo) {
    chips.push({
      key: 'date',
      label: `Emisión: ${formatDateRangeLabel(value.dateFrom, value.dateTo)}`,
    })
  }
  return chips
}

export function clearDocumentFilterField(
  value: DocumentFilterDraft,
  key: DocumentFilterChip['key'],
): DocumentFilterDraft {
  switch (key) {
    case 'status':
      return { ...value, status: 'all' }
    case 'date':
      return { ...value, dateFrom: '', dateTo: '' }
  }
}
