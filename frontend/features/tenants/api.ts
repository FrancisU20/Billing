import { api } from '@/lib/api/client'
import type { PaginatedData } from '@/lib/api/types'
import type { Tenant } from './types'

export const tenantsApi = {
  list: (nextToken?: string) =>
    api.get<PaginatedData<Tenant>>(`/tenants${nextToken ? `?next_token=${nextToken}` : ''}`),

  getById: (id: string) => api.get<Tenant>(`/tenants/${id}`),

  create: (body: Partial<Tenant>, idempotencyKey: string) =>
    api.post<Tenant>('/tenants', body, { idempotencyKey }),

  update: (id: string, body: Partial<Tenant>, idempotencyKey: string) =>
    api.patch<Tenant>(`/tenants/${id}`, body, { idempotencyKey }),

  setStatus: (id: string, status: 'active' | 'suspended', idempotencyKey: string) =>
    api.patch<Tenant>(`/tenants/${id}/status`, { status }, { idempotencyKey }),
}
