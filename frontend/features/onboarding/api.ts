import { api } from '@/lib/api/client'
import {
  onboardingOtpConfirmRequestSchema,
  onboardingOtpRequestResultSchema,
  onboardingRequestSchema,
  onboardingResultSchema,
} from './schemas'
import type { OnboardingOtpConfirmRequest, OnboardingRequest } from './schemas'

export const onboardingApi = {
  requestOtp: (body: OnboardingRequest, idempotencyKey: string) =>
    api.post(
      '/onboarding/otp/request',
      onboardingRequestSchema.parse(body),
      onboardingOtpRequestResultSchema,
      {
        idempotencyKey,
        auth: false,
      },
    ),

  confirmOtp: (body: OnboardingOtpConfirmRequest, idempotencyKey: string) =>
    api.post(
      '/onboarding/otp/confirm',
      onboardingOtpConfirmRequestSchema.parse(body),
      onboardingResultSchema,
      {
        idempotencyKey,
        auth: false,
      },
    ),
}
