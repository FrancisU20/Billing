import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'
import type { Plan } from '@/features/plans/schemas'

const MARKUP_PCT = 0.12

function roundHalfUp(value: number, decimals = 2): number {
  const factor = 10 ** decimals
  return Math.round(value * factor) / factor
}

function formatCurrency(value: number): string {
  return `$${value.toFixed(2)}`
}

interface Props {
  plan: Plan | null
  netAmount?: string // override from order result
  grossAmount?: string // override from order result
}

export function PriceBreakdown({ plan, netAmount, grossAmount }: Props) {
  const { semantic } = useTheme()

  if (!plan && !netAmount) return null

  const net = netAmount
    ? parseFloat(netAmount)
    : parseFloat(plan!.limit_cycle === 'year' ? plan!.annual_price : plan!.monthly_price)

  const gross = grossAmount ? parseFloat(grossAmount) : roundHalfUp(net * (1 + MARKUP_PCT))
  const markup = roundHalfUp(gross - net)
  const cycleLabel = plan?.limit_cycle === 'year' ? 'año' : 'mes'
  const planName = plan?.name ?? ''

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
      ]}
    >
      {planName ? (
        <View style={styles.row}>
          <Text style={[styles.label, { color: semantic.text.secondary }]}>Plan</Text>
          <Text style={[styles.value, { color: semantic.text.primary }]}>{planName}</Text>
        </View>
      ) : null}

      <View style={styles.row}>
        <Text style={[styles.label, { color: semantic.text.secondary }]}>
          Precio base ({cycleLabel})
        </Text>
        <Text style={[styles.value, { color: semantic.text.primary }]}>{formatCurrency(net)}</Text>
      </View>

      <View style={styles.row}>
        <Text style={[styles.label, { color: semantic.text.secondary }]}>
          Comisión procesamiento (12%)
        </Text>
        <Text style={[styles.value, { color: semantic.text.secondary }]}>
          +{formatCurrency(markup)}
        </Text>
      </View>

      <View style={[styles.divider, { backgroundColor: semantic.border.default }]} />

      <View style={styles.row}>
        <Text style={[styles.totalLabel, { color: semantic.text.primary }]}>Se te cobrará</Text>
        <Text style={[styles.totalValue, { color: semantic.accent.default }]}>
          {formatCurrency(gross)}/{cycleLabel}
        </Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 8,
    borderWidth: 1,
    padding: spacing[4],
    gap: spacing[2],
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: { fontSize: typography.size.sm },
  value: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  divider: { height: 1, marginVertical: spacing[1] },
  totalLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  totalValue: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
})
