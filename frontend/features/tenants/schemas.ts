import { z } from 'zod'
import { isPhoneInput } from '@/lib/utils/form-validators'
import { isValidRuc } from '@/lib/utils/ruc'

export const tenantStatusSchema = z.enum(['active', 'suspended', 'inactive'])
export const sriEnvironmentSchema = z.enum(['testing', 'production'])
export const planStatusSchema = z.enum(['active', 'expired'])

export const subscriptionStatusSchema = z
  .enum(['active', 'expired', 'none', 'pending_payment', 'payment_failed'])
  .optional()

export const tenantSchema = z.object({
  id: z.string().min(1),
  ruc: z.string().min(10).max(13),
  trade_name: z.string().min(1),
  legal_name: z.string().min(1),
  legal_rep_name: z.string().min(1),
  email: z.string().email(),
  phone: z.string().min(1),
  address: z.string().min(1),
  accounting_required: z.boolean(),
  sri_environment: sriEnvironmentSchema,
  status: tenantStatusSchema,
  plan_id: z.string().min(1),
  plan_status: planStatusSchema,
  plan_cycle_ends_at: z.string().nullable(),
  subscription_status: subscriptionStatusSchema,
  pending_order_id: z.string().nullable().optional(),
  cert_subject_ruc: z.string().nullable(),
  cert_expires_at: z.string().nullable(),
  cert_issuer: z.string().nullable(),
  cert_uploaded_at: z.string().nullable(),
  cert_expiry_alert_60_sent_at: z.string().nullable(),
  cert_expiry_alert_30_sent_at: z.string().nullable(),
  onboarding_completed_at: z.string().nullable(),
  created_at: z.string().min(1),
  updated_at: z.string().min(1),
  created_by: z.string(),
  version: z.coerce.number(),
})

export const tenantsPageSchema = z.object({
  items: z.array(tenantSchema),
  next_token: z.string().nullable(),
  has_more: z.boolean(),
  total: z.number().nullable().optional(),
})

export const createTenantSchema = z
  .object({
    ruc: z.string().min(10, 'RUC inválido').max(13, 'RUC inválido'),
    trade_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
    legal_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
    legal_rep_name: z
      .string()
      .trim()
      .min(2, 'Mínimo 2 caracteres')
      .max(200, 'Máximo 200 caracteres'),
    email: z.string().trim().email('Email inválido').max(200, 'Máximo 200 caracteres'),
    phone: z
      .string()
      .trim()
      .refine(isPhoneInput, 'Teléfono inválido')
      .max(20, 'Máximo 20 caracteres'),
    address: z.string().trim().min(5, 'Mínimo 5 caracteres').max(500, 'Máximo 500 caracteres'),
    accounting_required: z.boolean(),
    plan_id: z.string().min(1, 'El plan es requerido').max(36, 'Plan inválido'),
  })
  .strict()
  .refine((value) => isValidRuc(value.ruc), {
    path: ['ruc'],
    message: 'RUC ecuatoriano inválido',
  })

export const updateTenantSchema = z
  .object({
    trade_name: z
      .string()
      .trim()
      .min(2, 'Mínimo 2 caracteres')
      .max(200, 'Máximo 200 caracteres')
      .optional(),
    legal_name: z
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
      .refine(isPhoneInput, 'Teléfono inválido')
      .max(20, 'Máximo 20 caracteres')
      .optional(),
    address: z
      .string()
      .trim()
      .min(5, 'Mínimo 5 caracteres')
      .max(500, 'Máximo 500 caracteres')
      .optional(),
    accounting_required: z.boolean().optional(),
    sri_environment: sriEnvironmentSchema.optional(),
  })
  .strict()

export const toggleTenantStatusSchema = z
  .object({
    status: z.enum(['active', 'suspended', 'inactive']),
  })
  .strict()

export const tenantFormValuesSchema = z
  .object({
    ruc: z.string().trim().min(10, 'RUC inválido').max(13, 'RUC inválido'),
    trade_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
    legal_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
    legal_rep_name: z
      .string()
      .trim()
      .min(2, 'Mínimo 2 caracteres')
      .max(200, 'Máximo 200 caracteres'),
    email: z.string().trim().email('Email inválido').max(200, 'Máximo 200 caracteres'),
    phone: z
      .string()
      .trim()
      .refine(isPhoneInput, 'Teléfono inválido')
      .max(20, 'Máximo 20 caracteres'),
    address: z.string().trim().min(5, 'Mínimo 5 caracteres').max(500, 'Máximo 500 caracteres'),
    accounting_required: z.boolean(),
    sri_environment: sriEnvironmentSchema,
    plan_id: z.string().min(1, 'El plan es requerido'),
  })
  .refine((value) => isValidRuc(value.ruc), {
    path: ['ruc'],
    message: 'RUC ecuatoriano inválido',
  })

export const certificateMetadataSchema = z.object({
  cert_subject_ruc: z.string().nullable(),
  cert_expires_at: z.string().nullable(),
  cert_issuer: z.string().nullable(),
  cert_uploaded_at: z.string().nullable(),
})

export const certificateSchema = certificateMetadataSchema.extend({
  tenant_id: z.string(),
})

export const certificateUpdateSchema = z.object({
  certificate_b64: z.string().min(1, 'Selecciona tu certificado p12'),
  cert_password: z.string().min(1, 'La clave del certificado es requerida').max(200),
})

export const retryTenantOnboardingSchema = z.object({
  tenant_id: z.string().min(1),
  email: z.string().email(),
  status: z.literal('queued'),
})

export type Tenant = z.infer<typeof tenantSchema>
export type TenantStatus = z.infer<typeof tenantStatusSchema>
export type SriEnvironment = z.infer<typeof sriEnvironmentSchema>
export type PlanStatus = z.infer<typeof planStatusSchema>
export type TenantsPage = z.infer<typeof tenantsPageSchema>
export type CreateTenantInput = z.infer<typeof createTenantSchema>
export type UpdateTenantInput = z.infer<typeof updateTenantSchema>
export type ToggleTenantStatusInput = z.infer<typeof toggleTenantStatusSchema>
export type TenantFormValues = z.infer<typeof tenantFormValuesSchema>
export type CertificateMetadata = z.infer<typeof certificateMetadataSchema>
export type Certificate = z.infer<typeof certificateSchema>
export type CertificateUpdateInput = z.infer<typeof certificateUpdateSchema>
export type RetryTenantOnboardingResult = z.infer<typeof retryTenantOnboardingSchema>
