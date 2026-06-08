import { z } from 'zod'

export const tenantStatusSchema = z.enum(['active', 'suspended', 'inactive'])
export const sriEnvironmentSchema = z.enum(['testing', 'production'])
export const planStatusSchema = z.enum(['active', 'trial', 'expired', 'cancelled'])

export const tenantSchema = z.object({
  id: z.string().min(1),
  ruc: z.string().min(10).max(13),
  trade_name: z.string().min(1),
  legal_rep_name: z.string().min(1),
  email: z.string().email(),
  phone: z.string().min(1),
  address: z.string().min(1),
  sri_environment: sriEnvironmentSchema,
  status: tenantStatusSchema,
  plan_id: z.string().min(1),
  plan_status: planStatusSchema,
  trial_ends_at: z.string().nullable(),
  created_at: z.string().min(1),
  updated_at: z.string().min(1),
  created_by: z.string(),
  version: z.coerce.number(),
})

export const tenantsPageSchema = z.object({
  items: z.array(tenantSchema),
  next_token: z.string().nullable(),
  has_more: z.boolean(),
})

export const createTenantSchema = z
  .object({
    ruc: z.string().min(10, 'RUC inválido').max(13, 'RUC inválido'),
    trade_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
    legal_rep_name: z
      .string()
      .trim()
      .min(2, 'Mínimo 2 caracteres')
      .max(200, 'Máximo 200 caracteres'),
    email: z.string().trim().email('Email inválido').max(200, 'Máximo 200 caracteres'),
    phone: z.string().trim().min(7, 'Mínimo 7 caracteres').max(20, 'Máximo 20 caracteres'),
    address: z.string().trim().min(5, 'Mínimo 5 caracteres').max(500, 'Máximo 500 caracteres'),
    plan_id: z.string().min(1, 'El plan es requerido').max(36, 'Plan inválido'),
  })
  .strict()

export const updateTenantSchema = z
  .object({
    trade_name: z
      .string()
      .trim()
      .min(2, 'Mínimo 2 caracteres')
      .max(200, 'Máximo 200 caracteres')
      .optional(),
    legal_rep_name: z
      .string()
      .trim()
      .min(2, 'Mínimo 2 caracteres')
      .max(200, 'Máximo 200 caracteres')
      .optional(),
    email: z.string().trim().email('Email inválido').max(200, 'Máximo 200 caracteres').optional(),
    phone: z
      .string()
      .trim()
      .min(7, 'Mínimo 7 caracteres')
      .max(20, 'Máximo 20 caracteres')
      .optional(),
    address: z
      .string()
      .trim()
      .min(5, 'Mínimo 5 caracteres')
      .max(500, 'Máximo 500 caracteres')
      .optional(),
    sri_environment: sriEnvironmentSchema.optional(),
  })
  .strict()

export const toggleTenantStatusSchema = z
  .object({
    status: z.enum(['active', 'suspended', 'inactive']),
  })
  .strict()

export type Tenant = z.infer<typeof tenantSchema>
export type TenantStatus = z.infer<typeof tenantStatusSchema>
export type SriEnvironment = z.infer<typeof sriEnvironmentSchema>
export type PlanStatus = z.infer<typeof planStatusSchema>
export type TenantsPage = z.infer<typeof tenantsPageSchema>
export type CreateTenantInput = z.infer<typeof createTenantSchema>
export type UpdateTenantInput = z.infer<typeof updateTenantSchema>
export type ToggleTenantStatusInput = z.infer<typeof toggleTenantStatusSchema>
