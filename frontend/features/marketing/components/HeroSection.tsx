import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { useTheme } from '@/lib/theme-context'
import { colors, overlay, radius, spacing, typography } from '@/constants/tokens'
import { OnDarkButton } from './OnDarkButton'

const heroSignals = [
  { icon: 'checkmark-circle-outline', label: 'Facturas SRI listas' },
  { icon: 'shield-checkmark-outline', label: 'Pruebas incluidas' },
  { icon: 'mail-outline', label: 'RIDE y XML al comprador' },
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

      <View style={styles.layout}>
        <View style={styles.copy}>
          <Text style={styles.title}>CodeLabs Billing</Text>
          <Text style={styles.subtitle}>
            Facturación electrónica para empresas ecuatorianas: emite, autoriza y entrega
            comprobantes SRI desde un panel claro, con ambiente de pruebas incluido.
          </Text>
        </View>

        <View style={[styles.preview, { borderColor: overlay.border.default }]}>
          <View style={styles.previewHeader}>
            <View>
              <Text style={styles.previewEyebrow}>Factura autorizada</Text>
              <Text style={styles.previewTitle}>001-099-000000128</Text>
            </View>
            <Ionicons name="checkmark-circle" size={28} color={colors.teal[400]} />
          </View>
          <View style={styles.previewRows}>
            <PreviewRow label="Clave de acceso" value="190620260117921467390011001099..." />
            <PreviewRow label="Comprador" value="Cliente Demo S.A." />
            <PreviewRow label="Total" value="$115.00" strong />
          </View>
        </View>
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

function PreviewRow({
  label,
  value,
  strong = false,
}: {
  label: string
  value: string
  strong?: boolean
}) {
  return (
    <View style={styles.previewRow}>
      <Text style={styles.previewLabel}>{label}</Text>
      <Text style={[styles.previewValue, strong && styles.previewValueStrong]} numberOfLines={1}>
        {value}
      </Text>
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
  layout: { gap: spacing[6] },
  copy: { gap: spacing[3], maxWidth: 720 },
  title: {
    color: overlay.text.primary,
    fontSize: typography.size['4xl'],
    fontWeight: typography.weight.bold,
    letterSpacing: 0,
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
  preview: {
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing[4],
    gap: spacing[4],
    maxWidth: 520,
    backgroundColor: overlay.surface.default,
  },
  previewHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  previewEyebrow: {
    color: overlay.text.label,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
  },
  previewTitle: {
    color: overlay.text.primary,
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
  },
  previewRows: { gap: spacing[2] },
  previewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing[3],
  },
  previewLabel: { color: overlay.text.subtle, fontSize: typography.size.xs },
  previewValue: {
    color: overlay.text.primary,
    flex: 1,
    fontSize: typography.size.sm,
    textAlign: 'right',
  },
  previewValueStrong: { fontWeight: typography.weight.bold },
})
