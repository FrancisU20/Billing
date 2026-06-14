import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { Routes } from '@/constants/routes'
import { onboardingApi } from '../api'
import { useOnboardingStore } from '../store'
import type { OnboardingRequest } from '../schemas'

/**
 * Llama a /onboarding/otp/request, guarda la verificacion en el store y navega
 * al paso de OTP. Usado por RegisterDetailsScreen (self-service sin certificado)
 * y RegisterCertificateScreen (self-service con certificado).
 */
export function useRequestOtp() {
  const router = useRouter()
  const otpRequestIdempotencyKey = useOnboardingStore((state) => state.otpRequestIdempotencyKey)
  const setVerification = useOnboardingStore((state) => state.setVerification)

  return async (payload: OnboardingRequest) => {
    if (!otpRequestIdempotencyKey) return
    const verification = await onboardingApi.requestOtp(payload, otpRequestIdempotencyKey)
    setVerification(verification)
    router.push(Routes.public.registerOtp as Href)
  }
}
