import { api } from '@/lib/api/client'
import { onboardingRequestSchema, onboardingResultSchema } from './schemas'
import type { OnboardingRequest } from './schemas'

export const onboardingApi = {
  register: (body: OnboardingRequest, idempotencyKey: string) =>
    api.post('/onboarding', onboardingRequestSchema.parse(body), onboardingResultSchema, {
      idempotencyKey,
      auth: false,
    }),
}
