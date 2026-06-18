import { z } from 'zod'
import { api } from '@/lib/api/client'
import {
  createProductSchema,
  productSchema,
  productsPageSchema,
  updateProductSchema,
} from './schemas'
import { PRODUCTS_PAGE_SIZE } from './constants'
import type { CreateProductInput, ProductListFilters, UpdateProductInput } from './types'

function productsPath(filters: ProductListFilters = {}, nextToken?: string): string {
  const params = new URLSearchParams()
  params.set('limit', String(PRODUCTS_PAGE_SIZE))
  if (nextToken) params.set('next_token', nextToken)
  if (filters.q) params.set('q', filters.q)
  if (filters.sku) params.set('sku', filters.sku)
  if (filters.kind) params.set('kind', filters.kind)
  if (filters.status) params.set('status', filters.status)
  return `/products?${params.toString()}`
}

export const productsApi = {
  list: (filters?: ProductListFilters, nextToken?: string) =>
    api.get(productsPath(filters, nextToken), productsPageSchema),

  getById: (id: string) => api.get(`/products/${encodeURIComponent(id)}`, productSchema),

  create: (body: CreateProductInput, idempotencyKey: string) =>
    api.post('/products', createProductSchema.parse(body), productSchema, { idempotencyKey }),

  update: (id: string, body: UpdateProductInput, idempotencyKey: string) =>
    api.patch(
      `/products/${encodeURIComponent(id)}`,
      updateProductSchema.parse(body),
      productSchema,
      {
        idempotencyKey,
      },
    ),

  delete: (id: string, idempotencyKey: string) =>
    api.delete(`/products/${encodeURIComponent(id)}`, z.undefined(), { idempotencyKey }),
}
