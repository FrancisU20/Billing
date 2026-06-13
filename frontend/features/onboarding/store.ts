import { create } from 'zustand'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import type { Plan } from '@/features/plans/types'
import type { OnboardingResult, RegistrationFormValues } from './schemas'

interface OnboardingState {
  selectedPlan: Plan | null
  formValues: RegistrationFormValues | null
  idempotencyKey: string | null
  result: OnboardingResult | null
}

interface OnboardingActions {
  selectPlan: (plan: Plan) => void
  setFormValues: (values: RegistrationFormValues) => void
  setResult: (result: OnboardingResult) => void
  reset: () => void
}

const initialState: OnboardingState = {
  selectedPlan: null,
  formValues: null,
  idempotencyKey: null,
  result: null,
}

export const useOnboardingStore = create<OnboardingState & OnboardingActions>((set) => ({
  ...initialState,

  selectPlan: (plan: Plan) =>
    set((state) => ({
      selectedPlan: plan,
      idempotencyKey: state.idempotencyKey ?? createIdempotencyKey('onboarding'),
    })),

  setFormValues: (values: RegistrationFormValues) => set({ formValues: values }),

  setResult: (result: OnboardingResult) => set({ result }),

  reset: () => set(initialState),
}))
