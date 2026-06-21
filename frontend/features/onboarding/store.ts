import { create } from 'zustand'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import type { Plan } from '@/features/plans/types'
import type {
  CertificateFormValues,
  OnboardingOtpRequestResult,
  OnboardingResult,
  RegistrationFormValues,
} from './schemas'

interface OnboardingState {
  selectedPlan: Plan | null
  selectedBillingCycle: 'month' | 'year'
  formValues: RegistrationFormValues | null
  certificateValues: CertificateFormValues | null
  otpRequestIdempotencyKey: string | null
  otpConfirmIdempotencyKey: string | null
  verification: OnboardingOtpRequestResult | null
  result: OnboardingResult | null
}

interface OnboardingActions {
  selectPlan: (plan: Plan, billingCycle?: 'month' | 'year') => void
  setFormValues: (values: RegistrationFormValues) => void
  setCertificateValues: (values: CertificateFormValues | null) => void
  setVerification: (verification: OnboardingOtpRequestResult) => void
  setResult: (result: OnboardingResult) => void
  reset: () => void
}

const initialState: OnboardingState = {
  selectedPlan: null,
  selectedBillingCycle: 'month',
  formValues: null,
  certificateValues: null,
  otpRequestIdempotencyKey: null,
  otpConfirmIdempotencyKey: null,
  verification: null,
  result: null,
}

export const useOnboardingStore = create<OnboardingState & OnboardingActions>((set) => ({
  ...initialState,

  selectPlan: (plan: Plan, billingCycle: 'month' | 'year' = 'month') =>
    set((state) => ({
      selectedPlan: plan,
      selectedBillingCycle: billingCycle,
      otpRequestIdempotencyKey:
        state.otpRequestIdempotencyKey ?? createIdempotencyKey('onboarding-otp-request'),
      otpConfirmIdempotencyKey:
        state.otpConfirmIdempotencyKey ?? createIdempotencyKey('onboarding-otp-confirm'),
    })),

  setFormValues: (values: RegistrationFormValues) => set({ formValues: values }),

  setCertificateValues: (values: CertificateFormValues | null) =>
    set({ certificateValues: values }),

  setVerification: (verification: OnboardingOtpRequestResult) =>
    set({
      verification,
      otpRequestIdempotencyKey: createIdempotencyKey('onboarding-otp-request'),
    }),

  setResult: (result: OnboardingResult) => set({ result }),

  reset: () => set(initialState),
}))
