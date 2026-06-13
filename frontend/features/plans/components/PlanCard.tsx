import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { Button } from '@/components/ui/Button'
import { typography, radius, spacing, shadow, overlay } from '@/constants/tokens'
import { formatCurrency } from '@/lib/utils/format'
import { Badge } from '@/components/ui/Badge'
import { formatDocumentLimit, formatPlanLimit } from '../format'
import type { Plan } from '../types'

interface PlanCardProps {
  plan: Plan
  highlighted?: boolean
  onSelect: () => void
}

const features = [
  { key: 'includes_credit_notes', label: 'Notas de crédito' },
  { key: 'includes_withholdings', label: 'Retenciones' },
  { key: 'includes_delivery_notes', label: 'Guías de remisión' },
  { key: 'includes_api', label: 'Acceso a API' },
] as const

const CARD_MIN_HEIGHT = 520
const HEADER_MIN_HEIGHT = 76
const STATS_MIN_HEIGHT = 82

export function PlanCard({ plan, highlighted = false, onSelect }: PlanCardProps) {
  const { semantic } = useTheme()

  const cardBg = semantic.bg.elevated
  const cardBorder = highlighted ? semantic.accent.default : semantic.border.default
  const textMain = semantic.text.primary
  const textMuted = semantic.text.secondary
  const dividerBg = semantic.border.default
  const iconBg = highlighted ? semantic.accent.default : semantic.bg.muted
  const iconColor = highlighted ? overlay.text.primary : semantic.accent.default
  const statBg = semantic.bg.muted
  const statBorder = semantic.border.default
  const featureActiveBg = semantic.status.successBg

  const stats = [
    {
      icon: 'document-text-outline' as const,
      label: formatDocumentLimit(plan),
    },
    {
      icon: 'people-outline' as const,
      label: formatPlanLimit(plan.max_users, 'usuario', 'usuarios'),
    },
    {
      icon: 'business-outline' as const,
      label: formatPlanLimit(plan.max_locations, 'local', 'locales'),
    },
  ]

  return (
    <View
      style={[
        staticStyles.container,
        highlighted ? shadow.xl : shadow.sm,
        { backgroundColor: cardBg, borderColor: cardBorder, borderWidth: highlighted ? 2 : 1 },
      ]}
    >
      {highlighted ? (
        <View style={[staticStyles.ribbon, { backgroundColor: semantic.accent.default }]}>
          <Text style={[staticStyles.ribbonText, { color: overlay.text.primary }]}>
            Más popular
          </Text>
        </View>
      ) : null}

      <View style={staticStyles.topRow}>
        <View style={[staticStyles.planIcon, { backgroundColor: iconBg }]}>
          <Ionicons name="pricetag-outline" size={22} color={iconColor} />
        </View>
        {!plan.active ? <Badge label="Inactivo" variant="neutral" size="sm" /> : null}
      </View>

      <View style={staticStyles.header}>
        <Text style={[staticStyles.name, { color: textMain }]}>{plan.name}</Text>
        <Text style={[staticStyles.description, { color: textMuted }]} numberOfLines={2}>
          {plan.description}
        </Text>
      </View>

      <View style={staticStyles.priceBlock}>
        <View style={staticStyles.priceRow}>
          <Text style={[staticStyles.price, { color: textMain }]}>
            {formatCurrency(plan.monthly_price)}
          </Text>
          <Text style={[staticStyles.cycle, { color: textMuted }]}>/mes</Text>
        </View>
        <Text style={[staticStyles.billingHint, { color: textMuted }]}>Facturación mensual</Text>
      </View>

      <View style={[staticStyles.divider, { backgroundColor: dividerBg }]} />

      <View style={staticStyles.stats}>
        {stats.map((s) => (
          <View
            key={s.icon}
            style={[staticStyles.statPill, { backgroundColor: statBg, borderColor: statBorder }]}
          >
            <Ionicons name={s.icon} size={14} color={textMuted} />
            <Text style={[staticStyles.statLabel, { color: textMuted }]} numberOfLines={1}>
              {s.label}
            </Text>
          </View>
        ))}
      </View>

      <View style={staticStyles.features}>
        {features.map((f) => {
          const active = plan[f.key]
          const iconColor = active ? semantic.status.success : semantic.text.tertiary
          return (
            <View key={f.key} style={staticStyles.featureRow}>
              <View
                style={[staticStyles.featureIcon, active && { backgroundColor: featureActiveBg }]}
              >
                <Ionicons name={active ? 'checkmark' : 'remove'} size={14} color={iconColor} />
              </View>
              <Text
                style={[
                  staticStyles.featureLabel,
                  { color: active ? textMain : textMuted, opacity: active ? 1 : 0.58 },
                ]}
              >
                {f.label}
              </Text>
            </View>
          )
        })}
      </View>

      <View style={staticStyles.action}>
        <Button variant={highlighted ? 'primary' : 'outline'} fullWidth onPress={onSelect}>
          Elegir plan
        </Button>
      </View>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: {
    borderRadius: radius['2xl'],
    borderWidth: 1,
    flex: 1,
    padding: spacing[5],
    gap: spacing[4],
    minHeight: CARD_MIN_HEIGHT,
    overflow: 'hidden',
  },
  ribbon: {
    position: 'absolute',
    top: 0,
    right: 0,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1.5],
    borderBottomLeftRadius: radius.lg,
  },
  ribbonText: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  topRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  planIcon: {
    width: 48,
    height: 48,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 'auto',
  },
  header: { gap: spacing[2], minHeight: HEADER_MIN_HEIGHT },
  name: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    lineHeight: typography.size.xl * typography.lineHeight.tight,
  },
  description: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  priceBlock: { gap: spacing[1] },
  priceRow: { flexDirection: 'row', alignItems: 'baseline', gap: spacing[1] },
  price: {
    fontSize: typography.size['4xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['4xl'] * typography.lineHeight.tight,
    letterSpacing: -1,
  },
  cycle: { fontSize: typography.size.sm },
  billingHint: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  divider: { height: 1 },
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], minHeight: STATS_MIN_HEIGHT },
  statPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[1],
    borderWidth: 1,
    borderRadius: radius.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1.5],
  },
  statLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  features: { gap: spacing[3] },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  featureIcon: {
    width: 22,
    height: 22,
    borderRadius: radius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  featureLabel: { fontSize: typography.size.sm },
  action: { marginTop: 'auto' },
})
