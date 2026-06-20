import { z } from 'zod'
import { api } from '@/lib/api/client'
import { DEFAULT_PAGE_SIZE, type PageSize } from '@/constants/pagination'
import { clientSchema, clientsPageSchema, createClientSchema, updateClientSchema } from './schemas'
import type { ClientListFilters, CreateClientInput, UpdateClientInput } from './types'

function clientsPath(
  filters: ClientListFilters = {},
  nextToken?: string,
  limit: PageSize = DEFAULT_PAGE_SIZE,
): string {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (nextToken) params.set('next_token', nextToken)
  if (filters.q) params.set('q', filters.q)
  if (filters.identification) params.set('identification', filters.identification)
  if (filters.status) params.set('status', filters.status)
  if (filters.identification_type) params.set('identification_type', filters.identification_type)
  if (filters.created_from) params.set('created_from', filters.created_from)
  if (filters.created_to) params.set('created_to', filters.created_to)
  return `/clients?${params.toString()}`
}

export const clientsApi = {
  list: (filters?: ClientListFilters, nextToken?: string, limit?: PageSize) =>
    api.get(clientsPath(filters, nextToken, limit), clientsPageSchema),

  getById: (id: string) => api.get(`/clients/${encodeURIComponent(id)}`, clientSchema),

  create: (body: CreateClientInput, idempotencyKey: string) =>
    api.post('/clients', createClientSchema.parse(body), clientSchema, { idempotencyKey }),

  update: (id: string, body: UpdateClientInput, idempotencyKey: string) =>
    api.patch(`/clients/${encodeURIComponent(id)}`, updateClientSchema.parse(body), clientSchema, {
      idempotencyKey,
    }),

  delete: (id: string, idempotencyKey: string) =>
    api.delete(`/clients/${encodeURIComponent(id)}`, z.undefined(), { idempotencyKey }),

  setStatus: (id: string, status: 'active' | 'inactive', idempotencyKey: string) =>
    api.patch(`/clients/${encodeURIComponent(id)}`, { status }, clientSchema, { idempotencyKey }),
}
