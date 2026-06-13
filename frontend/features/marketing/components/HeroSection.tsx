import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { useTheme } from '@/lib/theme-context'
import { colors, overlay, radius, spacing, typography } from '@/constants/tokens'
import { OnDarkButton } from './OnDarkButton'

const heroSignals = [
  { icon: 'flash-outline', label: 'Aprobación SRI inmediata' },
  { icon: 'shield-checkmark-outline', label: 'Ambiente de pruebas incluido' },
  { icon: 'trending-up-outline', label: 'Crece con tu negocio' },
] as const

interface HeroSectionProps {
  onCreateAccount: () => void
  onLogin: () => void
}

export function HeroSection({ onCreateAccount, onLogin }: HeroSectionProps) {
  const { semantic } = useTheme()

  return (
    <View style={styles.container}>
      <View style={[styles.badge, { borderColor: overlay.border.default }]}>
        <Ionicons name="sparkles-outline" size={14} color={semantic.accent.default} />
        <Text style={[styles.badgeText, { color: semantic.accent.default }]}>
          SaaS de facturación electrónica · Ecuador
        </Text>
      </View>

      <View style={styles.copy}>
        <Text style={styles.title}>Factura electrónicamente sin complicarte con el SRI</Text>
        <Text style={styles.subtitle}>
          Emite facturas, notas de crédito, retenciones y guías de remisión desde un solo panel.
          Crea tu cuenta en minutos, prueba sin riesgo en el ambiente de pruebas del SRI y activa
          producción cuando estés listo.
        </Text>
      </View>

      <View style={styles.actions}>
        <Button variant="primary" size="lg" onPress={onCreateAccount}>
          Crear mi cuenta gratis
        </Button>
        <OnDarkButton size="lg" onPress={onLogin}>
          Ya tengo cuenta
        </OnDarkButton>
      </View>

      <View style={styles.signalRow}>
        {heroSignals.map((signal) => (
          <View
            key={signal.label}
            style={[styles.signalPill, { borderColor: overlay.border.default }]}
          >
            <Ionicons name={signal.icon} size={14} color={overlay.text.subtle} />
            <Text style={styles.signalText}>{signal.label}</Text>
          </View>
        ))}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.nav,
    paddingHorizontal: spacing[5],
    paddingTop: spacing[4],
    paddingBottom: spacing[10],
    gap: spacing[6],
  },
  badge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1.5],
  },
  badgeText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  copy: { gap: spacing[3], maxWidth: 720 },
  title: {
    color: overlay.text.primary,
    fontSize: typography.size['4xl'],
    fontWeight: typography.weight.bold,
    letterSpacing: -1,
    lineHeight: typography.size['4xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    color: overlay.text.muted,
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
  },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  signalRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  signalPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1.5],
  },
  signalText: {
    color: overlay.text.subtle,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.medium,
  },
})
