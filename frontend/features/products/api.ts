import { z } from 'zod'
import { api } from '@/lib/api/client'
import { DEFAULT_PAGE_SIZE, type PageSize } from '@/constants/pagination'
import {
  createProductSchema,
  discountCampaignSchema,
  productSchema,
  productsPageSchema,
  updateDiscountCampaignSchema,
  updateProductSchema,
} from './schemas'
import type {
  CreateProductInput,
  ProductListFilters,
  UpdateDiscountCampaignInput,
  UpdateProductInput,
} from './types'

function productsPath(
  filters: ProductListFilters = {},
  nextToken?: string,
  limit: PageSize = DEFAULT_PAGE_SIZE,
): string {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (nextToken) params.set('next_token', nextToken)
  if (filters.q) params.set('q', filters.q)
  if (filters.sku) params.set('sku', filters.sku)
  if (filters.kind) params.set('kind', filters.kind)
  if (filters.status) params.set('status', filters.status)
  return `/products?${params.toString()}`
}

export const productsApi = {
  list: (filters?: ProductListFilters, nextToken?: string, limit?: PageSize) =>
    api.get(productsPath(filters, nextToken, limit), productsPageSchema),

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

  setStatus: (id: string, status: 'ACTIVE' | 'INACTIVE', idempotencyKey: string) =>
    api.patch(`/products/${encodeURIComponent(id)}`, { status }, productSchema, {
      idempotencyKey,
    }),

  getDiscountCampaign: () => api.get('/products/discount-campaign', discountCampaignSchema),

  updateDiscountCampaign: (body: UpdateDiscountCampaignInput, idempotencyKey: string) =>
    api.put(
      '/products/discount-campaign',
      updateDiscountCampaignSchema.parse(body),
      discountCampaignSchema,
      { idempotencyKey },
    ),
}
