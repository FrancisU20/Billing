import React, { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import type { Href } from 'expo-router'
import { Routes } from '@/constants/routes'
import { spacing, typography } from '@/constants/tokens'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useTheme } from '@/lib/theme-context'
import { subscriptionsApi } from '../api'

type Phase = 'retrying' | 'failed' | 'success'

interface Props {
  tenantId: string
  onRetried: () => void
}

export function PaymentFailedBanner({ tenantId, onRetried }: Props) {
  const { semantic } = useTheme()
  const router = useRouter()
  const [phase, setPhase] = useState<Phase>('retrying')
  const [error, setError] = useState<string | null>(null)
  const retryKey = useRef(createIdempotencyKey('subscription-retry-payment'))
  const attempted = useRef(false)

  const doRetry = useCallback(async () => {
    setPhase('retrying')
    setError(null)
    retryKey.current = createIdempotencyKey('subscription-retry-payment')
    try {
      await subscriptionsApi.retryPayment(tenantId, retryKey.current)
      setPhase('success')
      onRetried()
    } catch (err) {
      setPhase('failed')
      setError(err instanceof Error ? err.message : 'El cobro automático falló.')
    }
  }, [tenantId, onRetried])

  // Auto-retry on mount
  useEffect(() => {
    if (attempted.current) return
    attempted.current = true
    doRetry()
  }, [doRetry])

  if (phase === 'success') return null

  return (
    <View
      style={[
        styles.banner,
        {
          backgroundColor:
            phase === 'retrying' ? semantic.status.warningBg : semantic.status.errorBg,
          borderColor: phase === 'retrying' ? semantic.status.warning : semantic.status.error,
        },
      ]}
    >
      <View style={styles.row}>
        {phase === 'retrying' ? (
          <ActivityIndicator size="small" color={semantic.status.warning} />
        ) : (
          <Ionicons name="alert-circle-outline" size={18} color={semantic.status.error} />
        )}
        <View style={styles.textGroup}>
          <Text
            style={[
              styles.title,
              {
                color: phase === 'retrying' ? semantic.status.warning : semantic.status.error,
              },
            ]}
          >
            {phase === 'retrying'
              ? 'Reintentando cobro automático...'
              : 'Pago fallido — acción requerida'}
          </Text>
          {error ? (
            <Text style={[styles.hint, { color: semantic.text.secondary }]}>{error}</Text>
          ) : null}
        </View>
      </View>

      {phase === 'failed' ? (
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.btn, { borderColor: semantic.status.error }]}
            onPress={doRetry}
            activeOpacity={0.7}
          >
            <Text style={[styles.btnText, { color: semantic.status.error }]}>
              Reintentar tarjeta guardada
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.btn, { borderColor: semantic.accent.default }]}
            onPress={() => router.push(Routes.tenant.billing as Href)}
            activeOpacity={0.7}
          >
            <Text style={[styles.btnText, { color: semantic.accent.default }]}>
              Pagar con tarjeta nueva
            </Text>
          </TouchableOpacity>
        </View>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  banner: {
    borderBottomWidth: 1,
    padding: spacing[4],
    gap: spacing[3],
  },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing[3] },
  textGroup: { flex: 1, gap: spacing[1] },
  title: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  hint: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.5 },
  actions: { flexDirection: 'row', gap: spacing[3], flexWrap: 'wrap' },
  btn: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: 6,
    borderWidth: 1,
  },
  btnText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
})
