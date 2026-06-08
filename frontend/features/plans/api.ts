import { api } from '@/lib/api/client'
import {
  createPlanSchema,
  planSchema,
  plansListSchema,
  togglePlanStatusSchema,
  updatePlanSchema,
} from './schemas'
import type {
  CreatePlanInput,
  PlanListFilters,
  TogglePlanStatusInput,
  UpdatePlanInput,
} from './types'

function listPath(filters: PlanListFilters = {}): string {
  const params = new URLSearchParams()
  if (filters.q) params.set('q', filters.q)
  if (filters.slug) params.set('slug', filters.slug)
  if (filters.status) params.set('status', filters.status)
  if (filters.limit_cycle) params.set('limit_cycle', filters.limit_cycle)
  if (filters.created_from) params.set('created_from', filters.created_from)
  if (filters.created_to) params.set('created_to', filters.created_to)
  const query = params.toString()
  return query ? `/plans?${query}` : '/plans'
}

export const plansApi = {
  list: (filters?: PlanListFilters) =>
    api.get(listPath(filters), plansListSchema, { auth: false }),

  getBySlug: (slug: string) => api.get(`/plans/${slug}`, planSchema, { auth: false }),

  create: (body: CreatePlanInput, idempotencyKey: string) =>
    api.post('/plans', createPlanSchema.parse(body), planSchema, { idempotencyKey }),

  update: (id: string, body: UpdatePlanInput, idempotencyKey: string) =>
    api.patch(`/plans/${id}`, updatePlanSchema.parse(body), planSchema, { idempotencyKey }),

  setStatus: (id: string, active: TogglePlanStatusInput['active'], idempotencyKey: string) =>
    api.patch(`/plans/${id}/status`, togglePlanStatusSchema.parse({ active }), planSchema, {
      idempotencyKey,
    }),
}
