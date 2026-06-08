import { api } from '@/lib/api/client'
import type { PaginatedData } from '@/lib/api/types'
import type { Plan } from './types'

export const plansApi = {
  list: () => api.get<PaginatedData<Plan>>('/plans', { auth: false }),

  getBySlug: (slug: string) => api.get<Plan>(`/plans/${slug}`, { auth: false }),

  create: (body: Partial<Plan>, idempotencyKey: string) =>
    api.post<Plan>('/plans', body, { idempotencyKey }),

  update: (id: string, body: Partial<Plan>, idempotencyKey: string) =>
    api.patch<Plan>(`/plans/${id}`, body, { idempotencyKey }),

  setStatus: (id: string, active: boolean, idempotencyKey: string) =>
    api.patch<Plan>(`/plans/${id}/status`, { active }, { idempotencyKey }),
}
