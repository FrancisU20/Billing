import React, { useCallback, useState } from 'react'
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { radius, shadow, spacing, typography } from '@/constants/tokens'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useTheme } from '@/lib/theme-context'
import { formatDate } from '@/lib/utils/format'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { retryWithBackoff } from '@/lib/utils/retry'
import { subscriptionsApi } from '@/features/subscriptions/api'
import { PayerForm, usePayerForm } from '@/features/subscriptions/components/PayerForm'
import { PriceBreakdown } from '@/features/subscriptions/components/PriceBreakdown'
import { useDLocalSmartFields } from '@/features/subscriptions/use-dlocal-smartfields'
import { use3dsFlow } from '@/features/subscriptions/use-3ds-flow'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useTenant } from '../hooks/useTenant'
import { usePlan } from '../hooks/usePlan'
import type { CreatePaymentResult } from '@/features/subscriptions/schemas'

function formatOptionalDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return formatDate(iso)
}

export function BillingScreen() {
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const { tenant, loading, refresh } = useTenant(tenantId)
  const { plan } = usePlan(tenant?.plan_id)

  const [order, setOrder] = useState<CreatePaymentResult | null>(null)
  const [createOrderKey] = useState(() => createIdempotencyKey('subscription-create-order'))
  const [renewalKey] = useState(() => createIdempotencyKey('subscription-renewal'))
  const [success, setSuccess] = useState(false)

  const payerForm = usePayerForm()
  const threeDs = use3dsFlow()

  const { fieldRef, sdkReady, sdkError } = useDLocalSmartFields({
    checkoutToken: order?.checkout_token,
    containerId: 'billing-card-field',
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
    submit: startRenewal,
  } = useFormSubmit(handleCreateOrder)

  const {
    submitting: confirming,
    error: confirmError,
    submit: confirmRenewal,
  } = useFormSubmit(async () => {
    if (!order || !tenantId || !tenant) return

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

    await retryWithBackoff(() =>
      subscriptionsApi.applyRenewal(tenantId, order.order_id, renewalKey),
    )
    setSuccess(true)
    setOrder(null)
    await refresh()
  })

  const handleCancelOrder = useCallback(() => {
    setOrder(null)
    payerForm.reset()
  }, [payerForm])

  if (loading) return <LoadingSpinner fullScreen label="Cargando..." />

  if (threeDs.state.phase === 'awaiting' || threeDs.state.phase === 'checking') {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <AppNavBar title="Verificación del banco" subtitle="Autenticación 3DS" />
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View
            style={[
              styles.card,
              { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
            ]}
          >
            <Text style={[styles.title, { color: semantic.text.primary }]}>
              Verificación requerida por tu banco
            </Text>
            <Text style={[styles.hint, { color: semantic.text.secondary }]}>
              Tu banco requiere autenticación adicional. Completa la verificación en la pestaña que
              se abrió y luego regresa aquí para confirmar el pago.
            </Text>
            <Button
              variant="primary"
              size="lg"
              fullWidth
              isLoading={threeDs.state.phase === 'checking'}
              onPress={() =>
                threeDs.checkStatus(async (orderId) => {
                  if (!tenantId) return
                  await retryWithBackoff(() =>
                    subscriptionsApi.applyRenewal(tenantId, orderId, renewalKey),
                  )
                  setSuccess(true)
                  await refresh()
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
        <AppNavBar title="Facturación" subtitle="Suscripción y pagos" />
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <View
            style={[
              styles.card,
              { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
            ]}
          >
            <Text style={[styles.title, { color: semantic.status.error }]}>
              {threeDs.state.error}
            </Text>
            <Button variant="primary" size="lg" fullWidth onPress={threeDs.reset}>
              Intentar de nuevo
            </Button>
          </View>
        </ScrollView>
      </View>
    )
  }

  const subStatus = tenant?.subscription_status
  const cycleEndsAt = tenant?.plan_cycle_ends_at
  const isActive = subStatus === 'active'
  const isExpired = subStatus === 'expired'
  const isPaymentFailed = subStatus === 'payment_failed'

  const statusLabel = isActive
    ? 'Activa'
    : isExpired
      ? 'Vencida'
      : isPaymentFailed
        ? 'Pago fallido'
        : 'Sin suscripción'

  const statusColor = isActive
    ? semantic.status.success
    : isExpired || isPaymentFailed
      ? semantic.status.error
      : semantic.text.secondary

  const statusBg = isActive
    ? semantic.status.successBg
    : isExpired || isPaymentFailed
      ? semantic.status.errorBg
      : semantic.bg.muted

  const renewalHint = isExpired
    ? 'Tu suscripción venció. Renuévala para reactivar el acceso.'
    : isPaymentFailed
      ? 'El cobro automático falló. Realiza el pago con una tarjeta diferente para reactivar tu cuenta.'
      : 'Extiende tu suscripción antes de que venza para no interrumpir el servicio.'

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Facturación" subtitle="Suscripción y pagos" />

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {success ? (
          <View
            style={[
              styles.successBox,
              { backgroundColor: semantic.status.successBg, borderColor: semantic.status.success },
            ]}
          >
            <Ionicons name="checkmark-circle-outline" size={20} color={semantic.status.success} />
            <Text style={[styles.successText, { color: semantic.status.success }]}>
              ¡Suscripción renovada con éxito!
            </Text>
          </View>
        ) : null}

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
                Estado de suscripción
              </Text>
            </View>
          </View>

          <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />

          {plan ? (
            <View style={styles.infoRow}>
              <Text style={[styles.label, { color: semantic.text.secondary }]}>Plan</Text>
              <Text style={[styles.value, { color: semantic.text.primary }]}>{plan.name}</Text>
            </View>
          ) : null}

          <View style={styles.infoRow}>
            <Text style={[styles.label, { color: semantic.text.secondary }]}>Estado</Text>
            <View style={[styles.badge, { backgroundColor: statusBg }]}>
              <Text style={[styles.badgeText, { color: statusColor }]}>{statusLabel}</Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Text style={[styles.label, { color: semantic.text.secondary }]}>Ciclo termina el</Text>
            <Text style={[styles.value, { color: semantic.text.primary }]}>
              {formatOptionalDate(cycleEndsAt)}
            </Text>
          </View>
        </View>

        {!success && tenant && (
          <View
            style={[
              styles.card,
              { backgroundColor: semantic.bg.elevated, borderColor: semantic.border.default },
            ]}
          >
            <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>
              {isPaymentFailed ? 'Pagar con tarjeta nueva' : 'Renovar suscripción'}
            </Text>
            <Text style={[styles.hint, { color: semantic.text.secondary }]}>{renewalHint}</Text>

            {!order ? (
              <>
                {createError ? <ApiErrorBanner error={createError} /> : null}
                <PriceBreakdown plan={plan} />
                <Button
                  variant="primary"
                  size="lg"
                  fullWidth
                  isLoading={creatingOrder}
                  onPress={() => startRenewal()}
                >
                  Pagar con tarjeta
                </Button>
              </>
            ) : (
              <>
                <PriceBreakdown
                  plan={plan}
                  netAmount={order.net_amount}
                  grossAmount={order.amount}
                />

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
                        nativeID="billing-card-field"
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
                      onPress={() => confirmRenewal()}
                    >
                      Confirmar pago
                    </Button>
                  </>
                )}

                <Button variant="ghost" size="sm" fullWidth onPress={handleCancelOrder}>
                  Cancelar
                </Button>
              </>
            )}
          </View>
        )}
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], gap: spacing[5], paddingBottom: spacing[12] },
  card: {
    borderRadius: radius.md,
    borderWidth: 1,
    padding: spacing[5],
    gap: spacing[4],
    ...shadow.md,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardTitle: { flex: 1 },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  divider: { height: 1 },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing[3],
  },
  label: { fontSize: typography.size.sm },
  value: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  badge: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: radius.full,
  },
  badgeText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  sectionTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  hint: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
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
  successBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    padding: spacing[4],
    borderRadius: radius.md,
    borderWidth: 1,
  },
  successText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
})
