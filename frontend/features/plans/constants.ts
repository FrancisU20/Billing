import type { LimitCycle } from './types'

export const PLAN_STATUS_OPTIONS = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
] as const

export const PLAN_LIMIT_CYCLE_OPTIONS: Array<{ value: LimitCycle; label: string }> = [
  { value: 'month', label: 'Mensual' },
  { value: 'year', label: 'Anual' },
]

export const PLAN_SEARCH_MODE_OPTIONS = [
  { value: 'q', label: 'General' },
  { value: 'slug', label: 'Slug exacto' },
] as const

export const PLAN_FEATURES = [
  { key: 'includes_credit_notes', label: 'Notas de crédito', icon: 'receipt-outline' },
  { key: 'includes_withholdings', label: 'Retenciones', icon: 'shield-checkmark-outline' },
  { key: 'includes_delivery_notes', label: 'Guías de remisión', icon: 'trail-sign-outline' },
  { key: 'includes_api', label: 'Acceso API', icon: 'code-slash-outline' },
] as const

export const UNLIMITED_LIMIT = -1

export const BOOLEAN_TOGGLE_OPTIONS: Array<{ value: 'yes' | 'no'; label: string }> = [
  { value: 'no', label: 'No' },
  { value: 'yes', label: 'Sí' },
]

export type PlanStatusFilter = (typeof PLAN_STATUS_OPTIONS)[number]['value']
export type PlanSearchMode = (typeof PLAN_SEARCH_MODE_OPTIONS)[number]['value']
