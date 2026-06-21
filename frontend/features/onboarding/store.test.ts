import { beforeEach, describe, expect, it } from 'vitest'
import type { Plan } from '@/features/plans/types'
import { useOnboardingStore } from './store'

const plan = {
  id: 'plan-basic',
  name: 'Basic',
  self_service: true,
} as Plan

describe('useOnboardingStore', () => {
  beforeEach(() => {
    useOnboardingStore.getState().reset()
  })

  it('rotates the OTP request idempotency key after a verification is received', () => {
    useOnboardingStore.getState().selectPlan(plan)
    const firstKey = useOnboardingStore.getState().otpRequestIdempotencyKey

    useOnboardingStore.getState().setVerification({
      verification_id: 'verification-1',
      expires_at: '2026-06-14T00:00:00+00:00',
      self_service: true,
    })

    const nextKey = useOnboardingStore.getState().otpRequestIdempotencyKey

    expect(firstKey).toMatch(/^onboarding-otp-request_/)
    expect(nextKey).toMatch(/^onboarding-otp-request_/)
    expect(nextKey).not.toBe(firstKey)
  })

  it('keeps a single OTP confirm idempotency key across re-selections and verifications', () => {
    useOnboardingStore.getState().selectPlan(plan)
    const firstKey = useOnboardingStore.getState().otpConfirmIdempotencyKey

    useOnboardingStore.getState().selectPlan(plan)
    useOnboardingStore.getState().setVerification({
      verification_id: 'verification-1',
      expires_at: '2026-06-14T00:00:00+00:00',
      self_service: true,
    })

    const nextKey = useOnboardingStore.getState().otpConfirmIdempotencyKey

    expect(firstKey).toMatch(/^onboarding-otp-confirm_/)
    expect(nextKey).toBe(firstKey)
  })

  it('defaults the billing cycle to month', () => {
    useOnboardingStore.getState().selectPlan(plan)
    expect(useOnboardingStore.getState().selectedBillingCycle).toBe('month')
  })

  it('stores the chosen billing cycle alongside the plan', () => {
    useOnboardingStore.getState().selectPlan(plan, 'year')
    expect(useOnboardingStore.getState().selectedBillingCycle).toBe('year')
  })

  it('stores and clears certificate values', () => {
    const certificate = {
      file_name: 'certificado.p12',
      certificate_b64: 'base64-data',
      cert_password: 'secret',
    }

    useOnboardingStore.getState().setCertificateValues(certificate)
    expect(useOnboardingStore.getState().certificateValues).toEqual(certificate)

    useOnboardingStore.getState().setCertificateValues(null)
    expect(useOnboardingStore.getState().certificateValues).toBeNull()
  })

  it('stores the onboarding result', () => {
    useOnboardingStore.getState().setResult({ tenant_id: 'tenant-1', email: 'owner@codelabs.com' })

    expect(useOnboardingStore.getState().result).toEqual({
      tenant_id: 'tenant-1',
      email: 'owner@codelabs.com',
    })
  })

  it('resets to the initial state', () => {
    useOnboardingStore.getState().selectPlan(plan, 'year')
    useOnboardingStore.getState().setCertificateValues({
      file_name: 'certificado.p12',
      certificate_b64: 'base64-data',
      cert_password: 'secret',
    })

    useOnboardingStore.getState().reset()

    expect(useOnboardingStore.getState().selectedPlan).toBeNull()
    expect(useOnboardingStore.getState().selectedBillingCycle).toBe('month')
    expect(useOnboardingStore.getState().certificateValues).toBeNull()
    expect(useOnboardingStore.getState().otpRequestIdempotencyKey).toBeNull()
    expect(useOnboardingStore.getState().otpConfirmIdempotencyKey).toBeNull()
  })
})
