export type LimitCycle = 'month' | 'year'

export interface Plan {
  id: string
  slug: string
  name: string
  description: string
  monthly_price: string
  annual_price: string
  document_limit: number
  limit_cycle: LimitCycle
  max_locations: number
  max_emission_points: number
  max_users: number
  includes_credit_notes: boolean
  includes_withholdings: boolean
  includes_delivery_notes: boolean
  includes_api: boolean
  order: number
  active: boolean
  version: number
  created_at: string
  updated_at: string
  created_by: string
}
