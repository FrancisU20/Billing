import { z } from 'zod'
import { isValidRuc } from '@/lib/utils/ruc'

export const onboardingRequestSchema = z
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
    phone: z.string().trim().min(7, 'Mínimo 7 caracteres').max(20, 'Máximo 20 caracteres'),
    address: z.string().trim().min(5, 'Mínimo 5 caracteres').max(500, 'Máximo 500 caracteres'),
    accounting_required: z.boolean(),
    plan_id: z.string().min(1, 'El plan es requerido').max(36, 'Plan inválido'),
  })
  .strict()

export const onboardingResultSchema = z.union([
  z.object({ tenant_id: z.string().min(1), email: z.string().min(1) }),
  z.object({ message: z.string().min(1) }),
])

export const registrationFormValuesSchema = z.object({
  ruc: z
    .string()
    .trim()
    .length(13, 'El RUC debe tener 13 dígitos')
    .refine(isValidRuc, 'RUC inválido'),
  trade_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
  legal_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
  legal_rep_name: z.string().trim().min(2, 'Mínimo 2 caracteres').max(200, 'Máximo 200 caracteres'),
  email: z.string().trim().email('Email inválido').max(200, 'Máximo 200 caracteres'),
  phone: z.string().trim().min(7, 'Mínimo 7 caracteres').max(20, 'Máximo 20 caracteres'),
  address: z.string().trim().min(5, 'Mínimo 5 caracteres').max(500, 'Máximo 500 caracteres'),
  accounting_required: z.boolean(),
})

export type OnboardingRequest = z.infer<typeof onboardingRequestSchema>
export type OnboardingResult = z.infer<typeof onboardingResultSchema>
export type RegistrationFormValues = z.infer<typeof registrationFormValuesSchema>
