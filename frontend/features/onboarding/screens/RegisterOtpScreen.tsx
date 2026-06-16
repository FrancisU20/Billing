import React, { useEffect, useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { onboardingApi } from '../api'
import { formValuesToOnboardingPayload } from '../form'
import { useRequestOtp } from '../hooks/useRequestOtp'
import { otpFormValuesSchema, type OtpFormValues } from '../schemas'
import { useOnboardingStore } from '../store'

function isPaidPlan(monthlyPrice: string, annualPrice: string): boolean {
  return parseFloat(monthlyPrice) > 0 || parseFloat(annualPrice) > 0
}

export function RegisterOtpScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const selectedPlan = useOnboardingStore((state) => state.selectedPlan)
  const formValues = useOnboardingStore((state) => state.formValues)
  const certificateValues = useOnboardingStore((state) => state.certificateValues)
  const verification = useOnboardingStore((state) => state.verification)
  const otpConfirmIdempotencyKey = useOnboardingStore((state) => state.otpConfirmIdempotencyKey)
  const setOtpValue = useOnboardingStore((state) => state.setOtpValue)
  const setResult = useOnboardingStore((state) => state.setResult)
  const requestOtp = useRequestOtp()
  const [resent, setResent] = useState(false)

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<OtpFormValues>({
    resolver: zodResolver(otpFormValuesSchema),
    defaultValues: { otp: '' },
  })

  useEffect(() => {
    if (!selectedPlan || !formValues || !verification) {
      router.replace(Routes.root as Href)
      return
    }
    if (selectedPlan.self_service && !certificateValues) {
      router.replace(Routes.public.registerCertificate as Href)
    }
  }, [certificateValues, formValues, selectedPlan, verification, router])

  const { submitting, error, submit } = useFormSubmit(async (values: OtpFormValues) => {
    if (!selectedPlan || !formValues || !verification || !otpConfirmIdempotencyKey) return

    const planIsPaid = isPaidPlan(selectedPlan.monthly_price, selectedPlan.annual_price)
    if (planIsPaid) {
      setOtpValue(values.otp.trim())
      router.push(Routes.public.registerPayment as Href)
      return
    }

    const result = await onboardingApi.confirmOtp(
      {
        ...formValuesToOnboardingPayload(formValues, selectedPlan.id),
        verification_id: verification.verification_id,
        otp: values.otp.trim(),
        certificate_b64: certificateValues?.certificate_b64,
        cert_password: certificateValues?.cert_password,
      },
      otpConfirmIdempotencyKey,
    )
    setResult(result)
    router.push(Routes.public.registerConfirm as Href)
  })

  const {
    submitting: resending,
    error: resendError,
    submit: resendOtp,
  } = useFormSubmit(async () => {
    if (!selectedPlan || !formValues) return
    setResent(false)
    await requestOtp(
      {
        ...formValuesToOnboardingPayload(formValues, selectedPlan.id),
        certificate_b64: certificateValues?.certificate_b64,
        cert_password: certificateValues?.cert_password,
      },
      { navigate: false },
    )
    setResent(true)
  })

  if (!selectedPlan || !formValues || !verification) return null

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: semantic.text.primary }]}>Verifica tu correo</Text>
        <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
          Enviamos un código de 6 dígitos a {formValues.email}.
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            styles.section,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <Controller
            control={control}
            name="otp"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Código"
                placeholder="123456"
                keyboardType="number-pad"
                leftIcon="keypad-outline"
                maxLength={6}
                error={errors.otp?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />

          <Text style={[styles.hint, { color: semantic.text.secondary }]}>
            El código expira pronto. Si no te llegó o caducó, solicita uno nuevo.
          </Text>

          {error ? <ApiErrorBanner error={error} /> : null}
          {resendError ? <ApiErrorBanner error={resendError} /> : null}
          {resent && !resendError ? (
            <Text style={[styles.hint, { color: semantic.status.success }]}>
              Te enviamos un nuevo código a {formValues.email}.
            </Text>
          ) : null}

          <Button
            variant="primary"
            size="lg"
            fullWidth
            isLoading={submitting}
            onPress={handleSubmit(submit)}
          >
            Completar registro
          </Button>

          <Button
            variant="outline"
            size="lg"
            fullWidth
            isLoading={resending}
            onPress={() => resendOtp()}
          >
            Reenviar código
          </Button>

          <Button variant="ghost" size="lg" fullWidth onPress={() => router.back()}>
            Volver
          </Button>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { gap: spacing[2], padding: spacing[5], paddingTop: spacing[8] },
  title: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
  section: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[4],
  },
  hint: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
