import { z } from 'zod'

export const productKindSchema = z.enum(['PRODUCT', 'SERVICE', 'PACKAGE', 'MEMBERSHIP', 'OTHER'])
export const productStatusSchema = z.enum(['ACTIVE', 'INACTIVE'])
export const productIvaRateSchema = z.enum(['15', '5', '0', 'EXENTO'])

export const productSchema = z.object({
  id: z.string().min(1),
  tenant_id: z.string().min(1),
  sku: z.string().min(1),
  name: z.string().min(1),
  description: z.string(),
  kind: productKindSchema,
  unit: z.string().min(1),
  unit_price: z.string().min(1),
  iva_rate: productIvaRateSchema,
  discount_percentage: z.string().nullable(),
  stock_enabled: z.boolean(),
  stock_quantity: z.string().nullable(),
  low_stock_threshold: z.string().nullable(),
  status: productStatusSchema,
  created_at: z.string().min(1),
  updated_at: z.string().min(1),
  created_by: z.string(),
  updated_by: z.string(),
  version: z.coerce.number(),
})

export const productsPageSchema = z.object({
  items: z.array(productSchema),
  next_token: z.string().nullable(),
  has_more: z.boolean(),
  total: z.number().nullable().optional(),
})

export const productFormSchema = z
  .object({
    sku: z.string().trim().min(1, 'Requerido').max(32, 'Máximo 32 caracteres'),
    name: z.string().trim().min(1, 'Requerido').max(160, 'Máximo 160 caracteres'),
    description: z.string().trim().max(500, 'Máximo 500 caracteres'),
    kind: productKindSchema,
    unit: z.string().trim().min(1, 'Requerido').max(25, 'Máximo 25 caracteres'),
    unit_price: z
      .string()
      .trim()
      .regex(/^\d+(\.\d{1,2})?$/, 'Precio inválido'),
    iva_rate: productIvaRateSchema,
    discount_percentage: z
      .string()
      .trim()
      .regex(/^\d+(\.\d{1,2})?$/, 'Descuento inválido')
      .refine((value) => Number(value) <= 100, 'El descuento no puede superar 100%')
      .or(z.literal('')),
    stock_enabled: z.boolean(),
    stock_quantity: z
      .string()
      .trim()
      .regex(/^\d+(\.\d{1,2})?$/, 'Stock inválido')
      .or(z.literal('')),
    low_stock_threshold: z
      .string()
      .trim()
      .regex(/^\d+(\.\d{1,2})?$/, 'Umbral inválido')
      .or(z.literal('')),
    status: productStatusSchema,
  })
  .strict()

const productPayloadBaseSchema = z.object({
  sku: z.string().trim().min(1).max(32),
  name: z.string().trim().min(1).max(160),
  description: z.string().trim().max(500),
  kind: productKindSchema,
  unit: z.string().trim().min(1).max(25),
  unit_price: z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,2})?$/),
  iva_rate: productIvaRateSchema,
  discount_percentage: z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,2})?$/)
    .nullable()
    .optional(),
  stock_enabled: z.boolean(),
  stock_quantity: z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,2})?$/)
    .nullable()
    .optional(),
  low_stock_threshold: z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,2})?$/)
    .nullable()
    .optional(),
})

export const createProductSchema = productPayloadBaseSchema
export const updateProductSchema = productPayloadBaseSchema
  .extend({ status: productStatusSchema })
  .partial()

export const discountCampaignSchema = z.object({
  active: z.boolean(),
  percentage: z.string().min(1),
  updated_at: z.string().min(1),
  updated_by: z.string(),
  version: z.coerce.number(),
})

export const updateDiscountCampaignSchema = z.object({
  active: z.boolean(),
  percentage: z
    .string()
    .trim()
    .regex(/^\d+(\.\d{1,2})?$/, 'Porcentaje inválido')
    .refine((value) => Number(value) <= 100, 'El porcentaje no puede superar 100%'),
})

export type ProductKind = z.infer<typeof productKindSchema>
export type ProductStatus = z.infer<typeof productStatusSchema>
export type ProductIvaRate = z.infer<typeof productIvaRateSchema>
export type Product = z.infer<typeof productSchema>
export type ProductsPage = z.infer<typeof productsPageSchema>
export type ProductFormValues = z.infer<typeof productFormSchema>
export type CreateProductInput = z.infer<typeof createProductSchema>
export type UpdateProductInput = z.infer<typeof updateProductSchema>
export type DiscountCampaign = z.infer<typeof discountCampaignSchema>
export type UpdateDiscountCampaignInput = z.infer<typeof updateDiscountCampaignSchema>
