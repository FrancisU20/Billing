import React, { useCallback, useState } from 'react'
import { Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
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
import { useDLocalSmartFields } from '@/features/subscriptions/use-dlocal-smartfields'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { useTenant } from '../hooks/useTenant'
import type { CreatePaymentResult } from '@/features/subscriptions/schemas'

export function BillingScreen() {
  const { semantic } = useTheme()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const { tenant, loading, refresh } = useTenant(tenantId)

  const [order, setOrder] = useState<CreatePaymentResult | null>(null)
  const [createOrderKey] = useState(() => createIdempotencyKey('subscription-create-order'))
  const [renewalKey] = useState(() => createIdempotencyKey('subscription-renewal'))
  const [success, setSuccess] = useState(false)
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [payerEmail, setPayerEmail] = useState('')
  const [documentType, setDocumentType] = useState<'CI' | 'RUC'>('CI')
  const [payerDocument, setPayerDocument] = useState('')

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

    const { token: cardToken } = await window.dlocalGo!.createCardToken(fieldRef.current, {
      name: `${firstName.trim()} ${lastName.trim()}`,
    })

    const confirmation = await subscriptionsApi.confirmPayment(order.order_id, {
      card_token: cardToken,
      client_first_name: firstName.trim(),
      client_last_name: lastName.trim(),
      client_email: payerEmail.trim(),
      client_document_type: documentType,
      client_document: payerDocument.trim(),
    })

    if (confirmation.redirect_url) {
      window.location.href = confirmation.redirect_url
      return
    }

    if (confirmation.status !== 'PAID') {
      throw new Error('El pago no fue confirmado por dLocal Go.')
    }

    await subscriptionsApi.applyRenewal(tenantId, order.order_id, renewalKey)
    setSuccess(true)
    setOrder(null)
    await refresh()
  })

  const handleCancelOrder = useCallback(() => {
    setOrder(null)
    setFirstName('')
    setLastName('')
    setPayerEmail('')
    setDocumentType('CI')
    setPayerDocument('')
  }, [])

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

                    <Text style={[styles.payerSectionLabel, { color: semantic.text.primary }]}>
                      Datos del pagador
                    </Text>

                    <View style={styles.fieldRow}>
                      <View style={[styles.fieldGroup, styles.fieldFlex]}>
                        <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                          Nombre
                        </Text>
                        <TextInput
                          value={firstName}
                          onChangeText={setFirstName}
                          placeholder="Nombre"
                          placeholderTextColor={semantic.text.secondary}
                          autoCapitalize="words"
                          autoCorrect={false}
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
                      <View style={[styles.fieldGroup, styles.fieldFlex]}>
                        <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                          Apellido
                        </Text>
                        <TextInput
                          value={lastName}
                          onChangeText={setLastName}
                          placeholder="Apellido"
                          placeholderTextColor={semantic.text.secondary}
                          autoCapitalize="words"
                          autoCorrect={false}
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
                    </View>

                    <View style={styles.fieldGroup}>
                      <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                        Email
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
                        Tipo de documento
                      </Text>
                      <View style={styles.docTypeRow}>
                        {(['CI', 'RUC'] as const).map((type) => (
                          <Pressable
                            key={type}
                            onPress={() => setDocumentType(type)}
                            style={[
                              styles.docTypeBtn,
                              {
                                borderColor:
                                  documentType === type
                                    ? semantic.accent.default
                                    : semantic.border.default,
                                backgroundColor:
                                  documentType === type ? semantic.accent.subtle : semantic.bg.page,
                              },
                            ]}
                          >
                            <Text
                              style={[
                                styles.docTypeBtnText,
                                {
                                  color:
                                    documentType === type
                                      ? semantic.accent.default
                                      : semantic.text.secondary,
                                },
                              ]}
                            >
                              {type === 'CI' ? 'Cédula' : 'RUC'}
                            </Text>
                          </Pressable>
                        ))}
                      </View>
                    </View>

                    <View style={styles.fieldGroup}>
                      <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>
                        Número de documento
                      </Text>
                      <TextInput
                        value={payerDocument}
                        onChangeText={setPayerDocument}
                        placeholder={documentType === 'CI' ? '10 dígitos' : '13 dígitos'}
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
                      isLoading={confirming}
                      disabled={
                        !sdkReady ||
                        !firstName.trim() ||
                        !lastName.trim() ||
                        !payerEmail.trim() ||
                        !payerDocument.trim()
                      }
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
  fieldGroup: { gap: spacing[1] },
  fieldFlex: { flex: 1 },
  fieldRow: { flexDirection: 'row', gap: spacing[3] },
  fieldLabel: { fontSize: typography.size.xs },
  payerSectionLabel: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    marginTop: spacing[1],
  },
  nameInput: {
    height: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing[3],
    fontSize: typography.size.sm,
  },
  docTypeRow: { flexDirection: 'row', gap: spacing[2] },
  docTypeBtn: {
    flex: 1,
    height: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  docTypeBtnText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  fieldError: { fontSize: typography.size.xs },
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
