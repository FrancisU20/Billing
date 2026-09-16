import { useCallback, useEffect, useRef, useState } from 'react'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { subscriptionsApi } from './api'
import type { CreatePaymentResult } from './schemas'

interface PaymentOrderInput {
  planId: string | null
  billingCycle: 'month' | 'year' | null
}

export function usePaymentOrder({ planId, billingCycle }: PaymentOrderInput) {
  const [order, setOrder] = useState<CreatePaymentResult | null>(null)
  const [createOrderKey] = useState(() => createIdempotencyKey('subscription-activate-create'))
  const [activateKey] = useState(() => createIdempotencyKey('subscription-activate'))
  const orderTriggered = useRef(false)

  const handleCreateOrder = useCallback(async () => {
    if (!planId || !billingCycle) return
    const result = await subscriptionsApi.createPayment(
      { plan_id: planId, currency: 'USD', billing_cycle: billingCycle },
      createOrderKey,
    )
    setOrder(result)
  }, [planId, billingCycle, createOrderKey])

  const {
    submitting: creatingOrder,
    error: createError,
    submit: startPayment,
  } = useFormSubmit(handleCreateOrder)

  useEffect(() => {
    if (!planId || !billingCycle || orderTriggered.current) return
    orderTriggered.current = true
    startPayment()
  }, [planId, billingCycle, startPayment])

  const resetOrder = useCallback(() => {
    setOrder(null)
    orderTriggered.current = false
  }, [])

  return { order, activateKey, creatingOrder, createError, startPayment, resetOrder }
}
