import React, { useCallback, useState } from 'react'
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Routes } from '@/constants/routes'
import { radius, shadow, spacing, typography } from '@/constants/tokens'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useTheme } from '@/lib/theme-context'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { useTenant } from '@/features/tenants/hooks/useTenant'
import { subscriptionsApi } from '../api'
import { PayerForm, usePayerForm } from '../components/PayerForm'
import { useDLocalSmartFields } from '../use-dlocal-smartfields'
import { use3dsFlow } from '../use-3ds-flow'
import type { CreatePaymentResult } from '../schemas'

export function ActivateSubscriptionScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const { tenant, loading: tenantLoading } = useTenant(tenantId)

  const [order, setOrder] = useState<CreatePaymentResult | null>(null)
  const [createOrderKey] = useState(() => createIdempotencyKey('subscription-activate-create'))
  const [activateKey] = useState(() => createIdempotencyKey('subscription-activate'))

  const payerForm = usePayerForm()
  const threeDs = use3dsFlow()

  const { fieldRef, sdkReady, sdkError } = useDLocalSmartFields({
    checkoutToken: order?.checkout_token,
    containerId: 'activate-card-field',
    semantic,
  })

  const handleCreateOrder = useCallback(async () => {
    if (!tenant) return
    const result = await subscriptionsApi.createPayment(
      { plan_id: tenant.plan_id, currency: 'USD' },
      createOrderKey,
    )
    setOrder(result)
  }, [tenant, createOrderKey])

  const {
    submitting: creatingOrder,
    error: createError,
    submit: startPayment,
  } = useFormSubmit(handleCreateOrder)

  const {
    submitting: confirming,
    error: confirmError,
    submit: confirmPayment,
  } = useFormSubmit(async () => {
    if (!order || !tenantId) return

    if (Platform.OS !== 'web' || !fieldRef.current) {
      throw new Error('El pago con tarjeta está disponible solo en la versión web.')
    }

    const { values } = payerForm
    const { token: cardToken } = await window.dlocalGo!.createCardToken(fieldRef.current, {
      name: `${values.firstName.trim()} ${values.lastName.trim()}`,
    })

    const confirmation = await subscriptionsApi.confirmPayment(order.order_id, {
      card_token: cardToken,
      client_first_name: values.firstName.trim(),
      client_last_name: values.lastName.trim(),
      client_email: values.payerEmail.trim(),
      client_document_type: values.documentType,
      client_document: values.payerDocument.trim(),
    })

    if (confirmation.redirect_url) {
      threeDs.startRedirect(confirmation.redirect_url, order.order_id)
      return
    }

    if (confirmation.status !== 'PAID') {
      throw new Error('El pago no fue confirmado por dLocal Go.')
    }

    await subscriptionsApi.activateSubscription(tenantId, order.order_id, activateKey)
    router.replace(Routes.tenant.dashboard as Href)
  })

  const handleCancel = useCallback(() => {
    setOrder(null)
    payerForm.reset()
  }, [payerForm])

  if (tenantLoading) return <LoadingSpinner fullScreen label="Cargando..." />

  if (threeDs.state.phase === 'awaiting' || threeDs.state.phase === 'checking') {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View
            style={[
              styles.card,
              { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
            ]}
          >
            <View style={styles.cardHeader}>
              <View style={[styles.iconWrap, { backgroundColor: semantic.accent.subtle }]}>
                <Ionicons
                  name="shield-checkmark-outline"
                  size={22}
                  color={semantic.accent.default}
                />
              </View>
              <View style={styles.cardTitle}>
                <Text style={[styles.title, { color: semantic.text.primary }]}>
                  Verificación del banco
                </Text>
                <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
                  Tu banco requiere autenticación adicional. Completa la verificación en la pestaña
                  que se abrió y luego regresa aquí.
                </Text>
              </View>
            </View>
            <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />
            <Button
              variant="primary"
              size="lg"
              fullWidth
              isLoading={threeDs.state.phase === 'checking'}
              onPress={() =>
                threeDs.checkStatus(async (orderId) => {
                  if (!tenantId) return
                  await subscriptionsApi.activateSubscription(tenantId, orderId, activateKey)
                  router.replace(Routes.tenant.dashboard as Href)
                })
              }
            >
              Ya completé la verificación
            </Button>
            <Button variant="ghost" size="sm" fullWidth onPress={threeDs.reset}>
              Cancelar
            </Button>
          </View>
        </ScrollView>
      </View>
    )
  }

  if (threeDs.state.phase === 'failed') {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View
            style={[
              styles.card,
              { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
            ]}
          >
            <View
              style={[
                styles.infoBox,
                { backgroundColor: semantic.status.errorBg, borderColor: semantic.status.error },
              ]}
            >
              <Ionicons name="alert-circle-outline" size={16} color={semantic.status.error} />
              <Text style={[styles.infoText, { color: semantic.status.error }]}>
                {threeDs.state.error}
              </Text>
            </View>
            <Button variant="primary" size="lg" fullWidth onPress={threeDs.reset}>
              Intentar de nuevo
            </Button>
          </View>
        </ScrollView>
      </View>
    )
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View
          style={[
            styles.card,
            { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.cardHeader}>
            <View style={[styles.iconWrap, { backgroundColor: semantic.accent.subtle }]}>
              <Ionicons name="card-outline" size={22} color={semantic.accent.default} />
            </View>
            <View style={styles.cardTitle}>
              <Text style={[styles.title, { color: semantic.text.primary }]}>
                Activar suscripción
              </Text>
              <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
                Completa el pago para activar tu cuenta y comenzar a emitir documentos.
              </Text>
            </View>
          </View>

          <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />

          {!order ? (
            <>
              {createError ? <ApiErrorBanner error={createError} /> : null}
              <Button
                variant="primary"
                size="lg"
                fullWidth
                isLoading={creatingOrder}
                onPress={() => startPayment()}
              >
                Pagar con tarjeta
              </Button>
            </>
          ) : (
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
                      nativeID="activate-card-field"
                      style={[
                        styles.fieldContainer,
                        {
                          borderColor: semantic.border.default,
                          backgroundColor: semantic.bg.page,
                        },
                      ]}
                    />
                  </View>

                  <PayerForm values={payerForm.values} setters={payerForm.setters} />

                  {confirmError ? <ApiErrorBanner error={confirmError} /> : null}

                  <Button
                    variant="primary"
                    size="lg"
                    fullWidth
                    isLoading={confirming}
                    disabled={!sdkReady || !payerForm.isComplete}
                    onPress={() => confirmPayment()}
                  >
                    Confirmar pago
                  </Button>
                </>
              )}

              <Button variant="ghost" size="sm" fullWidth onPress={handleCancel}>
                Cancelar
              </Button>
            </>
          )}
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], gap: spacing[5], paddingBottom: spacing[12] },
  card: {
    borderRadius: radius['2xl'],
    borderWidth: 1,
    padding: spacing[5],
    gap: spacing[4],
    ...shadow.md,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing[3] },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  cardTitle: { flex: 1, gap: spacing[1] },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  subtitle: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
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
  fieldContainer: {
    height: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    overflow: 'hidden',
  },
})
