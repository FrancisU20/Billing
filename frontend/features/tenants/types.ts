export type TenantStatus = 'active' | 'suspended' | 'pending'

export interface Tenant {
  id: string
  ruc: string
  business_name: string
  trade_name: string
  email: string
  phone: string
  address: string
  status: TenantStatus
  plan_id: string
  created_at: string
  updated_at: string
}
