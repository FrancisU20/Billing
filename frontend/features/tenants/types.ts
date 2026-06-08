export type TenantStatus   = 'active' | 'suspended' | 'pending'
export type SriEnvironment = 'testing' | 'production'
export type PlanStatus     = 'active' | 'inactive'

export interface Tenant {
  id:             string
  ruc:            string
  trade_name:     string
  legal_rep_name: string
  email:          string
  phone:          string
  address:        string
  sri_environment: SriEnvironment
  status:         TenantStatus
  plan_id:        string
  plan_status:    PlanStatus
  trial_ends_at:  string | null
  created_at:     string
  updated_at:     string
  created_by:     string
  version:        string
}
