import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { Routes } from '@/constants/routes'
import { onboardingApi } from '../api'
import { useOnboardingStore } from '../store'
import type { OnboardingRequest } from '../schemas'

/**
 * Llama a /onboarding/otp/request y guarda la verificacion en el store. Por defecto
 * navega al paso de OTP (usado por RegisterDetailsScreen y RegisterCertificateScreen);
 * con `{ navigate: false }` solo refresca la verificacion (reenvio desde RegisterOtpScreen).
 */
export function useRequestOtp() {
  const router = useRouter()
  const otpRequestIdempotencyKey = useOnboardingStore((state) => state.otpRequestIdempotencyKey)
  const setVerification = useOnboardingStore((state) => state.setVerification)

  return async (payload: OnboardingRequest, options?: { navigate?: boolean }) => {
    if (!otpRequestIdempotencyKey) return
    const verification = await onboardingApi.requestOtp(payload, otpRequestIdempotencyKey)
    setVerification(verification)
    if (options?.navigate ?? true) {
      router.push(Routes.public.registerOtp as Href)
    }
  }
}
