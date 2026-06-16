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
  formValues: RegistrationFormValues | null
  certificateValues: CertificateFormValues | null
  otpRequestIdempotencyKey: string | null
  otpConfirmIdempotencyKey: string | null
  createPaymentIdempotencyKey: string | null
  verification: OnboardingOtpRequestResult | null
  otpValue: string | null
  orderId: string | null
  result: OnboardingResult | null
}

interface OnboardingActions {
  selectPlan: (plan: Plan) => void
  setFormValues: (values: RegistrationFormValues) => void
  setCertificateValues: (values: CertificateFormValues | null) => void
  setVerification: (verification: OnboardingOtpRequestResult) => void
  setOtpValue: (otp: string) => void
  setOrderId: (orderId: string) => void
  setResult: (result: OnboardingResult) => void
  reset: () => void
}

const initialState: OnboardingState = {
  selectedPlan: null,
  formValues: null,
  certificateValues: null,
  otpRequestIdempotencyKey: null,
  otpConfirmIdempotencyKey: null,
  createPaymentIdempotencyKey: null,
  verification: null,
  otpValue: null,
  orderId: null,
  result: null,
}

export const useOnboardingStore = create<OnboardingState & OnboardingActions>((set) => ({
  ...initialState,

  selectPlan: (plan: Plan) =>
    set((state) => ({
      selectedPlan: plan,
      otpRequestIdempotencyKey:
        state.otpRequestIdempotencyKey ?? createIdempotencyKey('onboarding-otp-request'),
      otpConfirmIdempotencyKey:
        state.otpConfirmIdempotencyKey ?? createIdempotencyKey('onboarding-otp-confirm'),
      createPaymentIdempotencyKey:
        state.createPaymentIdempotencyKey ?? createIdempotencyKey('onboarding-create-payment'),
    })),

  setFormValues: (values: RegistrationFormValues) => set({ formValues: values }),

  setCertificateValues: (values: CertificateFormValues | null) =>
    set({ certificateValues: values }),

  setVerification: (verification: OnboardingOtpRequestResult) =>
    set({
      verification,
      otpRequestIdempotencyKey: createIdempotencyKey('onboarding-otp-request'),
    }),

  setOtpValue: (otp: string) => set({ otpValue: otp }),

  setOrderId: (orderId: string) => set({ orderId }),

  setResult: (result: OnboardingResult) => set({ result }),

  reset: () => set(initialState),
}))
