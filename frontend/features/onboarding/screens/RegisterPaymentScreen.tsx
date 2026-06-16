import React, { useCallback, useEffect, useState } from 'react'
import { Linking, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { subscriptionsApi } from '@/features/subscriptions/api'
import { onboardingApi } from '../api'
import { formValuesToOnboardingPayload } from '../form'
import { useOnboardingStore } from '../store'
import type { CreatePaymentResult } from '@/features/subscriptions/schemas'

export function RegisterPaymentScreen() {
  const { semantic } = useTheme()
  const router = useRouter()

  const selectedPlan = useOnboardingStore((state) => state.selectedPlan)
  const formValues = useOnboardingStore((state) => state.formValues)
  const certificateValues = useOnboardingStore((state) => state.certificateValues)
  const verification = useOnboardingStore((state) => state.verification)
  const otpValue = useOnboardingStore((state) => state.otpValue)
  const otpConfirmIdempotencyKey = useOnboardingStore((state) => state.otpConfirmIdempotencyKey)
  const setOrderId = useOnboardingStore((state) => state.setOrderId)
  const setResult = useOnboardingStore((state) => state.setResult)

  const [order, setOrder] = useState<CreatePaymentResult | null>(null)
  const [orderError, setOrderError] = useState<string | null>(null)
  const [paypalOpened, setPaypalOpened] = useState(false)

  useEffect(() => {
    if (!selectedPlan || !formValues || !verification || !otpValue) {
      router.replace(Routes.root as Href)
    }
  }, [selectedPlan, formValues, verification, otpValue, router])

  const createOrder = useCallback(async () => {
    if (!selectedPlan) return
    setOrderError(null)
    try {
      const result = await subscriptionsApi.createPayment({
        plan_id: selectedPlan.id,
        currency: 'USD',
      })
      setOrder(result)
    } catch {
      setOrderError('No se pudo crear la orden de pago. Intenta de nuevo.')
    }
  }, [selectedPlan])

  useEffect(() => {
    createOrder()
  }, [createOrder])

  const handleOpenPayPal = async () => {
    if (!order) return
    const url = subscriptionsApi.paypalApprovalUrl(order.order_id)
    await Linking.openURL(url)
    setPaypalOpened(true)
  }

  const {
    submitting,
    error,
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
            styles.section,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <View style={[styles.planRow, { borderBottomColor: semantic.border.default }]}>
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

          {orderError ? (
            <View>
              <Text style={[styles.errorText, { color: semantic.status.error }]}>{orderError}</Text>
              <Button variant="outline" size="md" fullWidth onPress={createOrder}>
                Reintentar
              </Button>
            </View>
          ) : !order ? (
            <Text style={[styles.hint, { color: semantic.text.secondary }]}>
              Preparando la orden de pago…
            </Text>
          ) : (
            <>
              <View
                style={[
                  styles.infoBox,
                  { backgroundColor: semantic.accent.subtle, borderColor: semantic.accent.default },
                ]}
              >
                <Ionicons
                  name="information-circle-outline"
                  size={18}
                  color={semantic.accent.default}
                />
                <Text style={[styles.infoText, { color: semantic.text.primary }]}>
                  Al presionar &quot;Pagar con PayPal&quot; serás redirigido a PayPal para autorizar
                  el pago. Regresa a esta pantalla una vez completado.
                </Text>
              </View>

              <Button variant="primary" size="lg" fullWidth onPress={handleOpenPayPal}>
                Pagar con PayPal
              </Button>

              {paypalOpened ? (
                <>
                  {error ? <ApiErrorBanner error={error} /> : null}
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
          )}

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
  planRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    paddingBottom: spacing[4],
    borderBottomWidth: 1,
  },
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
  errorText: { fontSize: typography.size.sm, textAlign: 'center' },
  hint: {
    fontSize: typography.size.sm,
    textAlign: 'center',
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
})
