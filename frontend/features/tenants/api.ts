import { api } from '@/lib/api/client'
import {
  createTenantSchema,
  tenantSchema,
  tenantsPageSchema,
  toggleTenantStatusSchema,
  updateTenantSchema,
} from './schemas'
import type { CreateTenantInput, ToggleTenantStatusInput, UpdateTenantInput } from './types'

function listPath(nextToken?: string): string {
  return `/tenants${nextToken ? `?next_token=${encodeURIComponent(nextToken)}` : ''}`
}

export const tenantsApi = {
  list: (nextToken?: string) => api.get(listPath(nextToken), tenantsPageSchema),

  getById: (id: string) => api.get(`/tenants/${id}`, tenantSchema),

  create: (body: CreateTenantInput, idempotencyKey: string) =>
    api.post('/tenants', createTenantSchema.parse(body), tenantSchema, { idempotencyKey }),

  update: (id: string, body: UpdateTenantInput, idempotencyKey: string) =>
    api.patch(`/tenants/${id}`, updateTenantSchema.parse(body), tenantSchema, { idempotencyKey }),

  setStatus: (id: string, status: ToggleTenantStatusInput['status'], idempotencyKey: string) =>
    api.patch(`/tenants/${id}/status`, toggleTenantStatusSchema.parse({ status }), tenantSchema, {
      idempotencyKey,
    }),
}
