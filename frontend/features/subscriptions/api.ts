import { api } from '@/lib/api/client'
import {
  activateSubscriptionResultSchema,
  applyRenewalResultSchema,
  confirmPaymentResultSchema,
  createPaymentResultSchema,
  paymentStatusSchema,
  retryPaymentResultSchema,
} from './schemas'

export const subscriptionsApi = {
  createPayment: (
    body: { plan_id: string; currency: string; billing_cycle?: 'month' | 'year' },
    idempotencyKey: string,
  ) =>
    api.post('/subscriptions/payments', body, createPaymentResultSchema, {
      auth: false,
      idempotencyKey,
    }),

  confirmPayment: (
    orderId: string,
    body: {
      card_token: string
      client_first_name: string
      client_last_name: string
      client_email: string
      client_document_type: string
      client_document: string
    },
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

  activateSubscription: (tenantId: string, orderId: string, idempotencyKey: string) =>
    api.post(
      `/tenants/${tenantId}/subscription/activate`,
      { order_id: orderId },
      activateSubscriptionResultSchema,
      { idempotencyKey },
    ),

  retryPayment: (tenantId: string, idempotencyKey: string) =>
    api.post(`/tenants/${tenantId}/subscription/retry-payment`, {}, retryPaymentResultSchema, {
      idempotencyKey,
    }),
}
