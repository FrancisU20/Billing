import { describe, expect, it } from 'vitest'
import { formValuesToOnboardingPayload, registrationFormDefaultValues } from './form'

const values = {
  ...registrationFormDefaultValues(),
  ruc: '1792146739001',
  trade_name: 'Wali',
  legal_name: 'Wali S.A.',
  legal_rep_name: 'Francisco Ulloa',
  email: 'owner@wali.ec',
  phone: '0999999999',
  address: 'Av Siempre Viva 123',
}

describe('formValuesToOnboardingPayload', () => {
  it('defaults billing_cycle to month when not provided', () => {
    const payload = formValuesToOnboardingPayload(values, 'plan-basic')
    expect(payload.billing_cycle).toBe('month')
  })

  it('forwards the chosen billing cycle', () => {
    const payload = formValuesToOnboardingPayload(values, 'plan-basic', 'year')
    expect(payload.billing_cycle).toBe('year')
    expect(payload.plan_id).toBe('plan-basic')
  })
})
