import React, { useCallback, useState } from 'react'
import { Linking, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { radius, shadow, spacing, typography } from '@/constants/tokens'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useTheme } from '@/lib/theme-context'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { subscriptionsApi } from '@/features/subscriptions/api'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useTenant } from '../hooks/useTenant'
import type { CreatePaymentResult } from '@/features/subscriptions/schemas'

export function BillingScreen() {
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const { tenant, loading, refresh } = useTenant(tenantId)

  const [order, setOrder] = useState<CreatePaymentResult | null>(null)
  const [paypalOpened, setPaypalOpened] = useState(false)
  const [renewalKey] = useState(() => createIdempotencyKey('subscription-renewal'))
  const [success, setSuccess] = useState(false)

  const handleCreateOrder = useCallback(async () => {
    if (!tenant) return
    const result = await subscriptionsApi.createPayment({
      plan_id: tenant.plan_id,
      currency: 'USD',
    })
    setOrder(result)
    const url = subscriptionsApi.paypalApprovalUrl(result.order_id)
    await Linking.openURL(url)
    setPaypalOpened(true)
  }, [tenant])

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
    if (!order || !tenantId) return

    const payment = await subscriptionsApi.getPayment(order.order_id)
    if (payment.status === 'APPROVED') {
      await subscriptionsApi.capturePayment(order.order_id)
    } else if (payment.status !== 'CAPTURED') {
      throw new Error(`El pago no ha sido completado en PayPal (estado: ${payment.status}).`)
    }

    await subscriptionsApi.applyRenewal(tenantId, order.order_id, renewalKey)
    setSuccess(true)
    setOrder(null)
    setPaypalOpened(false)
    await refresh()
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando..." />

  const subStatus = tenant?.subscription_status
  const cycleEndsAt = tenant?.plan_cycle_ends_at
  const isActive = subStatus === 'active'
  const isExpired = subStatus === 'expired'

  function formatDate(iso: string | null | undefined): string {
    if (!iso) return '—'
    return new Date(iso).toLocaleDateString('es-EC', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

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

          <View style={styles.infoRow}>
            <Text style={[styles.label, { color: semantic.text.secondary }]}>Estado</Text>
            <View
              style={[
                styles.badge,
                {
                  backgroundColor: isActive
                    ? semantic.status.successBg
                    : isExpired
                      ? semantic.status.errorBg
                      : semantic.bg.muted,
                },
              ]}
            >
              <Text
                style={[
                  styles.badgeText,
                  {
                    color: isActive
                      ? semantic.status.success
                      : isExpired
                        ? semantic.status.error
                        : semantic.text.secondary,
                  },
                ]}
              >
                {isActive ? 'Activa' : isExpired ? 'Vencida' : 'Sin suscripción'}
              </Text>
            </View>
          </View>

          <View style={styles.infoRow}>
            <Text style={[styles.label, { color: semantic.text.secondary }]}>Ciclo termina el</Text>
            <Text style={[styles.value, { color: semantic.text.primary }]}>
              {formatDate(cycleEndsAt)}
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
              Renovar suscripción
            </Text>
            <Text style={[styles.hint, { color: semantic.text.secondary }]}>
              {isExpired
                ? 'Tu suscripción venció. Renuévala para reactivar el acceso.'
                : 'Extiende tu suscripción antes de que venza para no interrumpir el servicio.'}
            </Text>

            {!order ? (
              <>
                {createError ? <ApiErrorBanner error={createError} /> : null}
                <Button
                  variant="primary"
                  size="lg"
                  fullWidth
                  isLoading={creatingOrder}
                  onPress={() => startRenewal()}
                >
                  Pagar con PayPal
                </Button>
              </>
            ) : (
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
                    Completa el pago en PayPal y regresa aquí para confirmar.
                  </Text>
                </View>

                {!paypalOpened ? (
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
                    Abrir PayPal
                  </Button>
                ) : (
                  <>
                    {confirmError ? <ApiErrorBanner error={confirmError} /> : null}
                    <Button
                      variant="secondary"
                      size="lg"
                      fullWidth
                      isLoading={confirming}
                      onPress={() => confirmRenewal()}
                    >
                      Ya completé el pago en PayPal
                    </Button>
                  </>
                )}

                <Button
                  variant="ghost"
                  size="sm"
                  fullWidth
                  onPress={() => {
                    setOrder(null)
                    setPaypalOpened(false)
                  }}
                >
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
    borderRadius: radius['2xl'],
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
