import type { LimitCycle } from './schemas'

export type {
  CreatePlanInput,
  LimitCycle,
  Plan,
  PlansList,
  TogglePlanStatusInput,
  UpdatePlanInput,
} from './schemas'

export interface PlanListFilters {
  q?: string
  slug?: string
  status?: 'active' | 'inactive'
  limit_cycle?: LimitCycle
  created_from?: string
  created_to?: string
}
