import { z } from 'zod'
import { isDecimalInput } from '@/lib/utils/form-validators'

export const limitCycleSchema = z.enum(['month', 'year'])

export const planSchema = z.object({
  id: z.string().min(1),
  slug: z.string().min(2).max(30),
  name: z.string().min(1),
  description: z.string(),
  monthly_price: z.string(),
  annual_price: z.string(),
  document_limit: z.number(),
  limit_cycle: limitCycleSchema,
  max_locations: z.number(),
  max_emission_points: z.number(),
  max_users: z.number(),
  pruebas_monthly_docs_limit: z.number(),
  pruebas_monthly_bulk_limit: z.number(),
  dedicated_queue: z.boolean(),
  self_service: z.boolean(),
  includes_credit_notes: z.boolean(),
  includes_withholdings: z.boolean(),
  includes_delivery_notes: z.boolean(),
  includes_api: z.boolean(),
  order: z.number(),
  active: z.boolean(),
  version: z.coerce.number(),
  created_at: z.string().min(1),
  updated_at: z.string().min(1),
  created_by: z.string(),
})

export const plansListSchema = z.object({
  items: z.array(planSchema),
})

const priceInputSchema = z.union([
  z.number().min(0),
  z.string().trim().refine(isDecimalInput, 'Precio inválido'),
])
const integerInputSchema = (min: number) =>
  z.preprocess(
    (value) => (typeof value === 'string' ? Number(value) : value),
    z.number().int().min(min),
  )

export const createPlanSchema = z
  .object({
    slug: z.string().regex(/^[a-z0-9_-]{2,30}$/, 'Slug inválido'),
    name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
    description: z.string().trim().max(300, 'Máximo 300 caracteres').default(''),
    monthly_price: priceInputSchema.default('0.00'),
    annual_price: priceInputSchema.default('0.00'),
    document_limit: integerInputSchema(-1),
    limit_cycle: limitCycleSchema.default('month'),
    max_locations: integerInputSchema(-1).default(1),
    max_emission_points: integerInputSchema(-1).default(1),
    max_users: integerInputSchema(-1).default(1),
    pruebas_monthly_docs_limit: integerInputSchema(-1).default(0),
    pruebas_monthly_bulk_limit: integerInputSchema(-1).default(0),
    dedicated_queue: z.boolean().default(false),
    self_service: z.boolean().default(true),
    includes_credit_notes: z.boolean().default(true),
    includes_withholdings: z.boolean().default(true),
    includes_delivery_notes: z.boolean().default(true),
    includes_api: z.boolean().default(false),
    order: z.number().int().min(0).default(0),
  })
  .strict()

export const updatePlanSchema = createPlanSchema.omit({ slug: true }).partial()

export const togglePlanStatusSchema = z
  .object({
    active: z.boolean(),
  })
  .strict()

export const planFormValuesSchema = z.object({
  slug: z.string().regex(/^[a-z0-9_-]{2,30}$/, 'Slug inválido'),
  name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(80, 'Máximo 80 caracteres'),
  description: z.string().trim().max(300, 'Máximo 300 caracteres'),
  monthly_price: z.string().trim().refine(isDecimalInput, 'Precio inválido'),
  annual_price: z.string().trim().refine(isDecimalInput, 'Precio inválido'),
  document_limit: z.number().int().min(0),
  document_limit_unlimited: z.boolean(),
  limit_cycle: limitCycleSchema,
  max_locations: z.number().int().min(0),
  max_locations_unlimited: z.boolean(),
  max_emission_points: z.number().int().min(0),
  max_emission_points_unlimited: z.boolean(),
  max_users: z.number().int().min(0),
  max_users_unlimited: z.boolean(),
  pruebas_monthly_docs_limit: z.number().int().min(0),
  pruebas_monthly_docs_limit_unlimited: z.boolean(),
  pruebas_monthly_bulk_limit: z.number().int().min(0),
  pruebas_monthly_bulk_limit_unlimited: z.boolean(),
  dedicated_queue: z.boolean(),
  self_service: z.boolean(),
  includes_credit_notes: z.boolean(),
  includes_withholdings: z.boolean(),
  includes_delivery_notes: z.boolean(),
  includes_api: z.boolean(),
  order: z.number().int().min(0),
})

export type LimitCycle = z.infer<typeof limitCycleSchema>
export type Plan = z.infer<typeof planSchema>
export type PlansList = z.infer<typeof plansListSchema>
export type CreatePlanInput = z.input<typeof createPlanSchema>
export type UpdatePlanInput = z.input<typeof updatePlanSchema>
export type TogglePlanStatusInput = z.infer<typeof togglePlanStatusSchema>
export type PlanFormValues = z.infer<typeof planFormValuesSchema>
