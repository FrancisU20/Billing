import { api } from '@/lib/api/client'
import {
  documentSchema,
  documentsPageSchema,
  documentsSummarySchema,
  emitDocumentResultSchema,
  emitDocumentSchema,
  rideUrlSchema,
} from './schemas'
import { DEFAULT_PAGE_SIZE, type PageSize } from '@/constants/pagination'
import type { DocumentListFilters, EmitDocumentInput } from './types'

function documentsPath(
  filters: DocumentListFilters = {},
  cursor?: string,
  limit: PageSize = DEFAULT_PAGE_SIZE,
): string {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  if (filters.status) params.set('status', filters.status)
  if (filters.serie) params.set('serie', filters.serie)
  if (filters.q) params.set('q', filters.q)
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  return `/documents?${params.toString()}`
}

export const documentsApi = {
  list: (filters?: DocumentListFilters, cursor?: string, limit?: PageSize) =>
    api.get(documentsPath(filters, cursor, limit), documentsPageSchema),

  summary: () => api.get('/documents/summary', documentsSummarySchema),

  getById: (id: string) => api.get(`/documents/${encodeURIComponent(id)}`, documentSchema),

  emit: (body: EmitDocumentInput, idempotencyKey: string) =>
    api.post('/documents', emitDocumentSchema.parse(body), emitDocumentResultSchema, {
      idempotencyKey,
    }),

  getRideUrl: (id: string) => api.get(`/documents/${encodeURIComponent(id)}/ride`, rideUrlSchema),

  getXmlUrl: (id: string) => api.get(`/documents/${encodeURIComponent(id)}/xml`, rideUrlSchema),

  annul: (id: string, reason: string, idempotencyKey: string) =>
    api.post(`/documents/${encodeURIComponent(id)}/annul`, { reason }, documentSchema, {
      idempotencyKey,
    }),
}
