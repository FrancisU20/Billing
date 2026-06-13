import type { PlanStatus, SriEnvironment, TenantStatus } from './types'

export const TENANTS_PAGE_SIZE = 30

export const TENANT_STATUS_OPTIONS: Array<{ value: TenantStatus | 'all'; label: string }> = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Activas' },
  { value: 'suspended', label: 'Suspendidas' },
  { value: 'inactive', label: 'Inactivas' },
]

export const TENANT_ENVIRONMENT_OPTIONS: Array<{ value: SriEnvironment | 'all'; label: string }> = [
  { value: 'all', label: 'Todos' },
  { value: 'testing', label: 'Pruebas' },
  { value: 'production', label: 'Producción' },
]

export const TENANT_PLAN_STATUS_OPTIONS: Array<{ value: PlanStatus | 'all'; label: string }> = [
  { value: 'all', label: 'Todos' },
  { value: 'active', label: 'Activo' },
  { value: 'expired', label: 'Expirado' },
]

export const ACCOUNTING_REQUIRED_OPTIONS: Array<{ value: 'yes' | 'no'; label: string }> = [
  { value: 'no', label: 'No' },
  { value: 'yes', label: 'Sí' },
]

export const TENANT_SEARCH_MODE_OPTIONS = [
  { value: 'q', label: 'General' },
  { value: 'ruc', label: 'RUC exacto' },
] as const

export const TENANT_STATUS_LABELS: Record<TenantStatus, string> = {
  active: 'Activa',
  suspended: 'Suspendida',
  inactive: 'Inactiva',
}

export const TENANT_ENVIRONMENT_LABELS: Record<SriEnvironment, string> = {
  testing: 'Pruebas',
  production: 'Producción',
}

export const TENANT_PLAN_STATUS_LABELS: Record<PlanStatus, string> = {
  active: 'Activo',
  expired: 'Expirado',
}

export type TenantSearchMode = (typeof TENANT_SEARCH_MODE_OPTIONS)[number]['value']
