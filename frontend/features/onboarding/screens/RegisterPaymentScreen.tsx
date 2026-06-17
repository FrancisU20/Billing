import React, { useCallback, useEffect, useState } from 'react'
import { Platform, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
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
import { useDLocalSmartFields } from '@/features/subscriptions/use-dlocal-smartfields'
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

  const { fieldRef, sdkReady, sdkError } = useDLocalSmartFields({
    checkoutToken: order?.checkout_token,
    containerId: 'dlocalgo-card-field',
    semantic,
  })

  const [cardholderName, setCardholderName] = useState('')
  const [nameError, setNameError] = useState<string | null>(null)
  const [payerEmail, setPayerEmail] = useState('')
  const [payerDocument, setPayerDocument] = useState('')

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

    if (!cardholderName.trim()) {
      setNameError('Ingresa el nombre del titular de la tarjeta.')
      return
    }
    setNameError(null)

    if (Platform.OS !== 'web' || !fieldRef.current) {
      throw new Error('El pago con tarjeta está disponible solo en la versión web.')
    }

    const { token: cardToken } = await window.dlocalGo!.createCardToken(fieldRef.current, {
      name: cardholderName.trim(),
    })

    await subscriptionsApi.confirmPayment(order.order_id, {
      card_token: cardToken,
      payer_name: cardholderName.trim(),
      payer_email: payerEmail.trim(),
      payer_document: payerDocument.trim(),
    })

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
            <LoadingSpinner compact label="Preparando formulario de pago..." />
          ) : createError ? (
            <>
              <ApiErrorBanner error={createError} />
              <Button variant="outline" size="md" fullWidth onPress={() => createOrder()}>
                Reintentar
              </Button>
            </>
          ) : order ? (
            <>
              {Platform.OS !== 'web' ? (
                <View
                  style={[
                    styles.infoBox,
                    {
                      backgroundColor: semantic.status.errorBg,
                      borderColor: semantic.status.error,
                    },
                  ]}
                >
                  <Ionicons
                    name="information-circle-outline"
                    size={16}
                    color={semantic.status.error}
                  />
                  <Text style={[styles.infoText, { color: semantic.status.error }]}>
                    El pago con tarjeta está disponible solo en la versión web.
                  </Text>
                </View>
              ) : sdkError ? (
                <View
                  style={[
                    styles.infoBox,
                    {
                      backgroundColor: semantic.status.errorBg,
                      borderColor: semantic.status.error,
                    },
                  ]}
                >
                  <Ionicons name="alert-circle-outline" size={16} color={semantic.status.error} />
                  <Text style={[styles.infoText, { color: semantic.status.error }]}>
                    {sdkError}
                  </Text>
                </View>
              ) : (
                <>
                  {!sdkReady && <LoadingSpinner compact label="Cargando formulario de pago..." />}

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                      Datos de tarjeta
                    </Text>
                    <View
                      nativeID="dlocalgo-card-field"
                      style={[
                        styles.fieldContainer,
                        { borderColor: semantic.border.default, backgroundColor: semantic.bg.page },
                      ]}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                      Nombre del titular
                    </Text>
                    <TextInput
                      value={cardholderName}
                      onChangeText={(v) => {
                        setCardholderName(v)
                        if (nameError) setNameError(null)
                      }}
                      placeholder="Como aparece en la tarjeta"
                      placeholderTextColor={semantic.text.secondary}
                      autoCapitalize="words"
                      autoCorrect={false}
                      style={[
                        styles.nameInput,
                        {
                          borderColor: nameError ? semantic.status.error : semantic.border.default,
                          backgroundColor: semantic.bg.page,
                          color: semantic.text.primary,
                        },
                      ]}
                    />
                    {nameError ? (
                      <Text style={[styles.fieldError, { color: semantic.status.error }]}>
                        {nameError}
                      </Text>
                    ) : null}
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                      Email del pagador
                    </Text>
                    <TextInput
                      value={payerEmail}
                      onChangeText={setPayerEmail}
                      placeholder="correo@ejemplo.com"
                      placeholderTextColor={semantic.text.secondary}
                      autoCapitalize="none"
                      autoCorrect={false}
                      keyboardType="email-address"
                      style={[
                        styles.nameInput,
                        {
                          borderColor: semantic.border.default,
                          backgroundColor: semantic.bg.page,
                          color: semantic.text.primary,
                        },
                      ]}
                    />
                  </View>

                  <View style={styles.fieldGroup}>
                    <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                      Cédula / RUC del pagador
                    </Text>
                    <TextInput
                      value={payerDocument}
                      onChangeText={setPayerDocument}
                      placeholder="10 o 13 dígitos"
                      placeholderTextColor={semantic.text.secondary}
                      autoCapitalize="none"
                      autoCorrect={false}
                      keyboardType="number-pad"
                      style={[
                        styles.nameInput,
                        {
                          borderColor: semantic.border.default,
                          backgroundColor: semantic.bg.page,
                          color: semantic.text.primary,
                        },
                      ]}
                    />
                  </View>

                  {confirmError ? <ApiErrorBanner error={confirmError} /> : null}

                  <Button
                    variant="primary"
                    size="lg"
                    fullWidth
                    isLoading={submitting}
                    disabled={
                      !sdkReady ||
                      !cardholderName.trim() ||
                      !payerEmail.trim() ||
                      !payerDocument.trim()
                    }
                    onPress={() => confirmPayment()}
                  >
                    Pagar ${price} USD
                  </Button>
                </>
              )}
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
  fieldGroup: { gap: spacing[1] },
  fieldLabel: { fontSize: typography.size.xs },
  nameInput: {
    height: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing[3],
    fontSize: typography.size.sm,
  },
  fieldError: { fontSize: typography.size.xs },
  fieldContainer: {
    height: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    overflow: 'hidden',
  },
})
