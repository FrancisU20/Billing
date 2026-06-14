import { api } from '@/lib/api/client'
import {
  certificateMetadataSchema,
  certificateSchema,
  certificateUpdateSchema,
  createTenantSchema,
  retryTenantOnboardingSchema,
  tenantSchema,
  tenantsPageSchema,
  toggleTenantStatusSchema,
  updateTenantSchema,
} from './schemas'
import { TENANTS_PAGE_SIZE } from './constants'
import type {
  CertificateUpdateInput,
  CreateTenantInput,
  ToggleTenantStatusInput,
  UpdateTenantInput,
} from './types'
import type { TenantListFilters } from './types'

function listPath(filters: TenantListFilters = {}, nextToken?: string): string {
  const params = new URLSearchParams()
  params.set('limit', String(TENANTS_PAGE_SIZE))
  if (nextToken) params.set('next_token', nextToken)
  if (filters.q) params.set('q', filters.q)
  if (filters.ruc) params.set('ruc', filters.ruc)
  if (filters.status) params.set('status', filters.status)
  if (filters.sri_environment) params.set('sri_environment', filters.sri_environment)
  if (filters.plan_status) params.set('plan_status', filters.plan_status)
  if (filters.created_from) params.set('created_from', filters.created_from)
  if (filters.created_to) params.set('created_to', filters.created_to)
  return `/tenants?${params.toString()}`
}

export const tenantsApi = {
  list: (filters?: TenantListFilters, nextToken?: string) =>
    api.get(listPath(filters, nextToken), tenantsPageSchema),

  getById: (id: string) => api.get(`/tenants/${encodeURIComponent(id)}`, tenantSchema),

  create: (body: CreateTenantInput, idempotencyKey: string) =>
    api.post('/tenants', createTenantSchema.parse(body), tenantSchema, { idempotencyKey }),

  update: (id: string, body: UpdateTenantInput, idempotencyKey: string) =>
    api.patch(`/tenants/${encodeURIComponent(id)}`, updateTenantSchema.parse(body), tenantSchema, {
      idempotencyKey,
    }),

  setStatus: (id: string, status: ToggleTenantStatusInput['status'], idempotencyKey: string) =>
    api.patch(
      `/tenants/${encodeURIComponent(id)}/status`,
      toggleTenantStatusSchema.parse({ status }),
      tenantSchema,
      {
        idempotencyKey,
      },
    ),

  delete: (id: string, idempotencyKey: string) =>
    api.delete(`/tenants/${encodeURIComponent(id)}`, tenantSchema.optional(), { idempotencyKey }),

  retryOnboarding: (id: string, idempotencyKey: string) =>
    api.post(
      `/tenants/${encodeURIComponent(id)}/onboarding/retry`,
      undefined,
      retryTenantOnboardingSchema,
      { idempotencyKey },
    ),

  getCertificate: (id: string) =>
    api.get(`/tenants/${encodeURIComponent(id)}/certificate`, certificateSchema),

  replaceCertificate: (id: string, body: CertificateUpdateInput, idempotencyKey: string) =>
    api.put(
      `/tenants/${encodeURIComponent(id)}/certificate`,
      certificateUpdateSchema.parse(body),
      certificateMetadataSchema,
      { idempotencyKey },
    ),
}
