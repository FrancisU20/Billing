import { z } from 'zod'

export const createPaymentResultSchema = z.object({
  order_id: z.string().min(1),
  amount: z.string().min(1),
  currency: z.string().min(1),
})

export const capturePaymentResultSchema = z.object({
  order_id: z.string().min(1),
  status: z.string().min(1),
  payer_id: z.string().min(1),
  payer_email: z.string().nullable(),
})

export const paymentStatusSchema = z.object({
  id: z.string().min(1),
  order_id: z.string().min(1),
  status: z.string().min(1),
  plan_id: z.string().min(1),
  amount: z.string(),
  currency: z.string(),
  tenant_id: z.string(),
  plan_cycle: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const applyRenewalResultSchema = z.object({
  tenant_id: z.string().min(1),
  plan_cycle_ends_at: z.string().min(1),
  subscription_status: z.string().min(1),
})

export type CreatePaymentResult = z.infer<typeof createPaymentResultSchema>
export type CapturePaymentResult = z.infer<typeof capturePaymentResultSchema>
export type PaymentStatus = z.infer<typeof paymentStatusSchema>
export type ApplyRenewalResult = z.infer<typeof applyRenewalResultSchema>
