import React, { useCallback, useEffect, useRef, useState } from 'react'
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { spacing, typography } from '@/constants/tokens'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { retryWithBackoff } from '@/lib/utils/retry'
import { useTheme } from '@/lib/theme-context'
import { subscriptionsApi } from '../api'

type Phase = 'activating' | 'failed'

interface Props {
  tenantId: string
  orderId: string
  onActivated: () => void
}

export function PendingActivationBanner({ tenantId, orderId, onActivated }: Props) {
  const { semantic } = useTheme()
  const [phase, setPhase] = useState<Phase>('activating')
  const [error, setError] = useState<string | null>(null)
  const keyRef = useRef(createIdempotencyKey('banner-activate'))

  const attempt = useCallback(async () => {
    setPhase('activating')
    setError(null)
    try {
      await retryWithBackoff(() =>
        subscriptionsApi.activateSubscription(tenantId, orderId, keyRef.current),
      )
      onActivated()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al activar la suscripción'
      setError(msg)
      setPhase('failed')
    }
  }, [tenantId, orderId, onActivated])

  useEffect(() => {
    attempt()
  }, [attempt])

  const bg = phase === 'failed' ? semantic.status.errorBg : semantic.status.warningBg
  const border = phase === 'failed' ? semantic.status.error : semantic.status.warning
  const textColor = phase === 'failed' ? semantic.status.error : semantic.status.warning

  return (
    <View style={[styles.banner, { backgroundColor: bg, borderColor: border }]}>
      {phase === 'activating' ? (
        <>
          <ActivityIndicator size="small" color={textColor} />
          <Text style={[styles.text, { color: textColor }]}>
            Tu pago fue procesado. Activando tu cuenta...
          </Text>
        </>
      ) : (
        <>
          <Ionicons name="alert-circle-outline" size={16} color={textColor} />
          <Text style={[styles.text, { color: textColor, flex: 1 }]}>
            {error ?? 'No se pudo activar la cuenta. Reintenta o contacta soporte.'}
          </Text>
          <TouchableOpacity onPress={attempt} style={styles.retryBtn}>
            <Text style={[styles.retryText, { color: textColor }]}>Reintentar</Text>
          </TouchableOpacity>
        </>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
  },
  text: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    flexShrink: 1,
  },
  retryBtn: {
    paddingHorizontal: spacing[2],
  },
  retryText: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.bold,
    textDecorationLine: 'underline',
  },
})
