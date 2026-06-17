import { z } from 'zod'

export const createPaymentResultSchema = z.object({
  order_id: z.string().min(1),
  checkout_token: z.string().min(1),
  amount: z.string().min(1), // gross: what the client is charged
  currency: z.string().min(1),
  net_amount: z.string().min(1), // plan base price before markup
  markup_pct: z.string().min(1), // e.g. "12"
})

export const confirmPaymentResultSchema = z.object({
  order_id: z.string().min(1),
  status: z.string().min(1),
  payer_id: z.string().nullable(),
  payer_email: z.string().nullable(),
  redirect_url: z.string().nullable().optional(),
})

export const paymentStatusSchema = z.object({
  order_id: z.string().min(1),
  status: z.string().min(1),
  plan_id: z.string().min(1),
  amount: z.string(),
  currency: z.string(),
  tenant_id: z.string().nullable(),
  plan_cycle: z.string(),
  created_at: z.string(),
  confirmed_at: z.string().nullable(),
})

export const applyRenewalResultSchema = z.object({
  tenant_id: z.string().min(1),
  plan_cycle_ends_at: z.string().min(1),
  subscription_status: z.string().min(1),
})

export const activateSubscriptionResultSchema = z.object({
  tenant_id: z.string().min(1),
  plan_cycle_ends_at: z.string().min(1),
  subscription_status: z.string().min(1),
})

export const retryPaymentResultSchema = z.object({
  tenant_id: z.string().min(1),
  plan_cycle_ends_at: z.string().min(1),
  subscription_status: z.string().min(1),
})

export type CreatePaymentResult = z.infer<typeof createPaymentResultSchema>
export type ConfirmPaymentResult = z.infer<typeof confirmPaymentResultSchema>
export type PaymentStatus = z.infer<typeof paymentStatusSchema>
export type ApplyRenewalResult = z.infer<typeof applyRenewalResultSchema>
export type ActivateSubscriptionResult = z.infer<typeof activateSubscriptionResultSchema>
export type RetryPaymentResult = z.infer<typeof retryPaymentResultSchema>
