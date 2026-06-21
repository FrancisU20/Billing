import { onboardingBaseRequestSchema } from './schemas'
import type { OnboardingRequest, RegistrationFormValues } from './schemas'

export function registrationFormDefaultValues(): RegistrationFormValues {
  return {
    ruc: '',
    trade_name: '',
    legal_name: '',
    legal_rep_name: '',
    email: '',
    phone: '',
    address: '',
    accounting_required: false,
  }
}

export function formValuesToOnboardingPayload(
  values: RegistrationFormValues,
  planId: string,
  billingCycle: 'month' | 'year' = 'month',
): OnboardingRequest {
  return onboardingBaseRequestSchema.parse({
    ruc: values.ruc.trim(),
    trade_name: values.trade_name.trim(),
    legal_name: values.legal_name.trim(),
    legal_rep_name: values.legal_rep_name.trim(),
    email: values.email.trim(),
    phone: values.phone.trim(),
    address: values.address.trim(),
    accounting_required: values.accounting_required,
    plan_id: planId,
    billing_cycle: billingCycle,
  })
}
