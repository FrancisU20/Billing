import { api } from '@/lib/api/client'
import { documentSchema, documentsPageSchema, emitDocumentSchema, rideUrlSchema } from './schemas'
import { DOCUMENTS_PAGE_SIZE } from './constants'
import type { DocumentListFilters, EmitDocumentInput } from './types'

function documentsPath(filters: DocumentListFilters = {}, cursor?: string): string {
  const params = new URLSearchParams()
  params.set('limit', String(DOCUMENTS_PAGE_SIZE))
  if (cursor) params.set('cursor', cursor)
  if (filters.status) params.set('status', filters.status)
  if (filters.serie) params.set('serie', filters.serie)
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  return `/documents?${params.toString()}`
}

export const documentsApi = {
  list: (filters?: DocumentListFilters, cursor?: string) =>
    api.get(documentsPath(filters, cursor), documentsPageSchema),

  getById: (id: string) => api.get(`/documents/${encodeURIComponent(id)}`, documentSchema),

  emit: (body: EmitDocumentInput, idempotencyKey: string) =>
    api.post('/documents', emitDocumentSchema.parse(body), documentSchema, { idempotencyKey }),

  getRideUrl: (id: string) => api.get(`/documents/${encodeURIComponent(id)}/ride`, rideUrlSchema),
}
