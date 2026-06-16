import { api } from '@/lib/api/client'
import { config } from '@/constants/config'
import {
  applyRenewalResultSchema,
  capturePaymentResultSchema,
  createPaymentResultSchema,
  paymentStatusSchema,
} from './schemas'

function paypalApprovalUrl(orderId: string): string {
  const base =
    config.env === 'prod'
      ? 'https://www.paypal.com/checkoutnow'
      : 'https://www.sandbox.paypal.com/checkoutnow'
  return `${base}?token=${orderId}`
}

export const subscriptionsApi = {
  createPayment: (body: { plan_id: string; currency: string }) =>
    api.post('/subscriptions/payments', body, createPaymentResultSchema, { auth: false }),

  capturePayment: (orderId: string) =>
    api.post(`/subscriptions/payments/${orderId}/capture`, {}, capturePaymentResultSchema, {
      auth: false,
    }),

  getPayment: (orderId: string) =>
    api.get(`/subscriptions/payments/${orderId}`, paymentStatusSchema, { auth: false }),

  applyRenewal: (tenantId: string, orderId: string, idempotencyKey: string) =>
    api.post(
      `/tenants/${tenantId}/subscription/renew`,
      { order_id: orderId },
      applyRenewalResultSchema,
      { idempotencyKey },
    ),

  paypalApprovalUrl,
}
