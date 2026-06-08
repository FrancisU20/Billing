import type { PlanStatus, SriEnvironment, TenantStatus } from './schemas'

export type {
  CreateTenantInput,
  PlanStatus,
  SriEnvironment,
  Tenant,
  TenantStatus,
  TenantsPage,
  ToggleTenantStatusInput,
  UpdateTenantInput,
} from './schemas'

export interface TenantListFilters {
  q?: string
  ruc?: string
  status?: TenantStatus
  sri_environment?: SriEnvironment
  plan_status?: PlanStatus
  created_from?: string
  created_to?: string
}
