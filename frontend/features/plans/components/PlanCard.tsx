import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, radius, spacing, shadow } from '@/constants/tokens'
import { formatCurrency } from '@/lib/utils/format'
import { Badge } from '@/components/ui/Badge'
import type { Plan } from '../types'

interface PlanCardProps { plan: Plan; highlighted?: boolean }

const features = [
  { key: 'includes_credit_notes',   label: 'Notas de crédito' },
  { key: 'includes_withholdings',   label: 'Retenciones' },
  { key: 'includes_delivery_notes', label: 'Guías de remisión' },
  { key: 'includes_api',            label: 'Acceso a API' },
] as const

export function PlanCard({ plan, highlighted = false }: PlanCardProps) {
  const { semantic } = useTheme()

  const cardBg = semantic.bg.elevated
  const cardBorder = highlighted ? semantic.accent.default : semantic.border.default
  const textMain = semantic.text.primary
  const textMuted = semantic.text.secondary
  const dividerBg = semantic.border.default
  const iconBg = highlighted ? semantic.accent.subtle : semantic.bg.muted
  const iconColor = semantic.accent.default
  const statBg = semantic.bg.muted
  const statBorder = semantic.border.default
  const featureActiveBg = semantic.status.successBg

  const stats = [
    { icon: 'document-text-outline' as const, label: `${plan.document_limit.toLocaleString()} docs/mes` },
    { icon: 'people-outline' as const, label: `${plan.max_users} usuarios` },
    { icon: 'business-outline' as const, label: `${plan.max_locations} locales` },
  ]

  return (
    <View style={[staticStyles.container, highlighted && shadow.xl, { backgroundColor: cardBg, borderColor: cardBorder }]}>
      <View style={[staticStyles.accentRail, { backgroundColor: highlighted ? semantic.accent.default : semantic.accent.alt }]} />

      <View style={staticStyles.topRow}>
        <View style={[staticStyles.planIcon, { backgroundColor: iconBg }]}>
          <Ionicons name="pricetag-outline" size={20} color={iconColor} />
        </View>
        {highlighted ? (
          <View style={[staticStyles.popularBadge, { backgroundColor: semantic.accent.subtle }]}>
            <Text style={[staticStyles.popularText, { color: semantic.accent.default }]}>Recomendado</Text>
          </View>
        ) : null}
        {!plan.active ? (
          <Badge label="Inactivo" variant="neutral" size="sm" />
        ) : null}
      </View>

      <View style={staticStyles.header}>
        <Text style={[staticStyles.name, { color: textMain }]}>{plan.name}</Text>
        <Text style={[staticStyles.description, { color: textMuted }]}>{plan.description}</Text>
      </View>

      <View style={staticStyles.priceBlock}>
        <View style={staticStyles.priceRow}>
          <Text style={[staticStyles.price, { color: textMain }]}>{formatCurrency(plan.monthly_price)}</Text>
          <Text style={[staticStyles.cycle, { color: textMuted }]}>/mes</Text>
        </View>
        <Text style={[staticStyles.billingHint, { color: textMuted }]}>Facturación mensual</Text>
      </View>

      <View style={[staticStyles.divider, { backgroundColor: dividerBg }]} />

      <View style={staticStyles.stats}>
        {stats.map((s) => (
          <View key={s.label} style={[staticStyles.statPill, { backgroundColor: statBg, borderColor: statBorder }]}>
            <Ionicons name={s.icon} size={14} color={textMuted} />
            <Text style={[staticStyles.statLabel, { color: textMuted }]} numberOfLines={1}>{s.label}</Text>
          </View>
        ))}
      </View>

      <View style={staticStyles.features}>
        {features.map((f) => {
          const active = plan[f.key]
          const iconColor = active
            ? semantic.status.success
            : semantic.text.tertiary
          return (
            <View key={f.key} style={staticStyles.featureRow}>
              <View style={[staticStyles.featureIcon, active && { backgroundColor: featureActiveBg }]}>
                <Ionicons name={active ? 'checkmark' : 'remove'} size={14} color={iconColor} />
              </View>
              <Text style={[staticStyles.featureLabel, { color: active ? textMain : textMuted, opacity: active ? 1 : 0.58 }]}>
                {f.label}
              </Text>
            </View>
          )
        })}
      </View>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { borderRadius: radius['2xl'], borderWidth: 1, padding: spacing[5], gap: spacing[4], overflow: 'hidden' },
  accentRail: { position: 'absolute', left: 0, top: 0, bottom: 0, width: 4 },
  topRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  planIcon: { width: 44, height: 44, borderRadius: radius.lg, alignItems: 'center', justifyContent: 'center', marginRight: 'auto' },
  popularBadge: { alignSelf: 'flex-start', borderRadius: radius.full, paddingHorizontal: spacing[3], paddingVertical: spacing[1] },
  popularText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  header: { gap: spacing[2] },
  name: { fontSize: typography.size.xl, fontWeight: typography.weight.bold, lineHeight: typography.size.xl * typography.lineHeight.tight },
  description: { fontSize: typography.size.sm, lineHeight: typography.size.sm * typography.lineHeight.normal },
  priceBlock: { gap: spacing[1] },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: spacing[1] },
  price: { fontSize: typography.size['3xl'], fontWeight: typography.weight.bold, lineHeight: typography.size['3xl'] * typography.lineHeight.tight },
  cycle: { fontSize: typography.size.sm },
  billingHint: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  divider: { height: 1 },
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  statPill: { flexDirection: 'row', alignItems: 'center', gap: spacing[1], borderWidth: 1, borderRadius: radius.full, paddingHorizontal: spacing[3], paddingVertical: spacing[2] - 2 },
  statLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  features: { gap: spacing[3] },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  featureIcon: { width: 22, height: 22, borderRadius: radius.full, alignItems: 'center', justifyContent: 'center' },
  featureLabel: { fontSize: typography.size.sm },
})
