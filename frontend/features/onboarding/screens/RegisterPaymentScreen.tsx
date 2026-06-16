import React, { useCallback, useEffect, useState } from 'react'
import { Linking, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Routes } from '@/constants/routes'
import { radius, shadow, spacing, typography } from '@/constants/tokens'
import { useAsync } from '@/lib/hooks/useAsync'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { subscriptionsApi } from '@/features/subscriptions/api'
import { onboardingApi } from '../api'
import { formValuesToOnboardingPayload } from '../form'
import { useOnboardingStore } from '../store'

export function RegisterPaymentScreen() {
  const { semantic } = useTheme()
  const router = useRouter()

  const selectedPlan = useOnboardingStore((state) => state.selectedPlan)
  const formValues = useOnboardingStore((state) => state.formValues)
  const certificateValues = useOnboardingStore((state) => state.certificateValues)
  const verification = useOnboardingStore((state) => state.verification)
  const otpValue = useOnboardingStore((state) => state.otpValue)
  const otpConfirmIdempotencyKey = useOnboardingStore((state) => state.otpConfirmIdempotencyKey)
  const createPaymentIdempotencyKey = useOnboardingStore(
    (state) => state.createPaymentIdempotencyKey,
  )
  const setOrderId = useOnboardingStore((state) => state.setOrderId)
  const setResult = useOnboardingStore((state) => state.setResult)

  const [paypalOpened, setPaypalOpened] = useState(false)

  useEffect(() => {
    if (!selectedPlan || !formValues || !verification || !otpValue) {
      router.replace(Routes.root as Href)
    }
  }, [selectedPlan, formValues, verification, otpValue, router])

  const createOrderFn = useCallback(async () => {
    return subscriptionsApi.createPayment(
      { plan_id: selectedPlan!.id, currency: 'USD' },
      createPaymentIdempotencyKey!,
    )
  }, [selectedPlan, createPaymentIdempotencyKey])

  const {
    data: order,
    loading: creatingOrder,
    error: createError,
    execute: createOrder,
  } = useAsync(createOrderFn)

  useEffect(() => {
    if (!selectedPlan) return
    createOrder()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const {
    submitting,
    error: confirmError,
    submit: confirmPayment,
  } = useFormSubmit(async () => {
    if (
      !order ||
      !selectedPlan ||
      !formValues ||
      !verification ||
      !otpValue ||
      !otpConfirmIdempotencyKey
    )
      return

    const payment = await subscriptionsApi.getPayment(order.order_id)
    if (payment.status === 'APPROVED') {
      await subscriptionsApi.capturePayment(order.order_id)
    } else if (payment.status !== 'CAPTURED') {
      throw new Error(`El pago no ha sido completado en PayPal (estado: ${payment.status}).`)
    }

    setOrderId(order.order_id)

    const result = await onboardingApi.confirmOtp(
      {
        ...formValuesToOnboardingPayload(formValues, selectedPlan.id),
        verification_id: verification.verification_id,
        otp: otpValue,
        certificate_b64: certificateValues?.certificate_b64,
        cert_password: certificateValues?.cert_password,
        order_id: order.order_id,
      },
      otpConfirmIdempotencyKey,
    )
    setResult(result)
    router.push(Routes.public.registerConfirm as Href)
  })

  if (!selectedPlan || !formValues || !verification || !otpValue) return null

  const price =
    selectedPlan.limit_cycle === 'year' ? selectedPlan.annual_price : selectedPlan.monthly_price
  const cycleLabel = selectedPlan.limit_cycle === 'year' ? 'anuales' : 'mensuales'

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: semantic.text.primary }]}>Pago de suscripción</Text>
        <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
          Completa el pago para activar tu cuenta.
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            styles.card,
            { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.planRow}>
            <View style={[styles.planIcon, { backgroundColor: semantic.accent.subtle }]}>
              <Ionicons name="pricetag-outline" size={20} color={semantic.accent.default} />
            </View>
            <View style={styles.planInfo}>
              <Text style={[styles.planName, { color: semantic.text.primary }]}>
                {selectedPlan.name}
              </Text>
              <Text style={[styles.planPrice, { color: semantic.accent.default }]}>
                ${price} USD {cycleLabel}
              </Text>
            </View>
          </View>

          <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />

          {creatingOrder ? (
            <LoadingSpinner compact label="Preparando orden de pago..." />
          ) : createError ? (
            <>
              <ApiErrorBanner error={createError} />
              <Button variant="outline" size="md" fullWidth onPress={() => createOrder()}>
                Reintentar
              </Button>
            </>
          ) : order ? (
            <>
              <View
                style={[
                  styles.infoBox,
                  {
                    backgroundColor: semantic.accent.subtle,
                    borderColor: semantic.accent.default,
                  },
                ]}
              >
                <Ionicons
                  name="information-circle-outline"
                  size={16}
                  color={semantic.accent.default}
                />
                <Text style={[styles.infoText, { color: semantic.text.primary }]}>
                  Al presionar &quot;Pagar con PayPal&quot; serás redirigido a PayPal para autorizar
                  el pago. Regresa a esta pantalla una vez completado.
                </Text>
              </View>

              <Button
                variant="primary"
                size="lg"
                fullWidth
                onPress={async () => {
                  const url = subscriptionsApi.paypalApprovalUrl(order.order_id)
                  await Linking.openURL(url)
                  setPaypalOpened(true)
                }}
              >
                Pagar con PayPal
              </Button>

              {paypalOpened ? (
                <>
                  {confirmError ? <ApiErrorBanner error={confirmError} /> : null}
                  <Button
                    variant="secondary"
                    size="lg"
                    fullWidth
                    isLoading={submitting}
                    onPress={() => confirmPayment()}
                  >
                    Ya completé el pago en PayPal
                  </Button>
                </>
              ) : null}
            </>
          ) : null}

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
  card: {
    borderRadius: radius['2xl'],
    borderWidth: 1,
    padding: spacing[5],
    gap: spacing[4],
    ...shadow.md,
  },
  planRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  planIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  planInfo: { flex: 1, gap: spacing[1] },
  planName: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  planPrice: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  divider: { height: 1 },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing[2],
    padding: spacing[3],
    borderRadius: radius.sm,
    borderWidth: 1,
  },
  infoText: {
    flex: 1,
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
