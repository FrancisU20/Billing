import { api } from '@/lib/api/client'
import {
  createPlanSchema,
  planSchema,
  plansListSchema,
  togglePlanStatusSchema,
  updatePlanSchema,
} from './schemas'
import type { CreatePlanInput, TogglePlanStatusInput, UpdatePlanInput } from './types'

export const plansApi = {
  list: () => api.get('/plans', plansListSchema, { auth: false }),

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
