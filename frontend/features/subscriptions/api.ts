import { api } from '@/lib/api/client'
import {
  applyRenewalResultSchema,
  confirmPaymentResultSchema,
  createPaymentResultSchema,
  paymentStatusSchema,
} from './schemas'

export const subscriptionsApi = {
  createPayment: (body: { plan_id: string; currency: string }, idempotencyKey: string) =>
    api.post('/subscriptions/payments', body, createPaymentResultSchema, {
      auth: false,
      idempotencyKey,
    }),

  confirmPayment: (
    orderId: string,
    body: { card_token: string; payer_name: string; payer_email: string; payer_document: string },
  ) =>
    api.post(`/subscriptions/payments/${orderId}/confirm`, body, confirmPaymentResultSchema, {
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
}
