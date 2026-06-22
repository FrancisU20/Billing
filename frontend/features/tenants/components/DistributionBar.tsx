import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import type { BadgeVariant } from '@/components/ui/Badge'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

interface DistributionBarProps {
  label: string
  count: number
  total: number
  /** Mismo vocabulario de color que `Badge` — evita que cada pantalla invente su propio
   * color suelto (ver `chart.primary`/`chart.secondary` que reemplazo esto, sin ningun
   * significado de estado detras). */
  variant: BadgeVariant
  formatValue?: (count: number) => string
}

export function DistributionBar({
  label,
  count,
  total,
  variant,
  formatValue = (value) => String(value),
}: DistributionBarProps) {
  const { semantic } = useTheme()
  const pct = total > 0 ? Math.round((count / total) * 100) : 0

  const variantColor: Record<BadgeVariant, string> = {
    success: semantic.status.success,
    warning: semantic.status.warning,
    error: semantic.status.error,
    neutral: semantic.text.secondary,
    primary: semantic.accent.default,
    accent: semantic.accent.alt,
  }

  return (
    <View style={styles.row}>
      <View style={styles.header}>
        <Text style={[styles.label, { color: semantic.text.primary }]} numberOfLines={1}>
          {label}
        </Text>
        <Text style={[styles.value, { color: semantic.text.secondary }]}>
          {formatValue(count)} ({pct}%)
        </Text>
      </View>
      <View style={[styles.track, { backgroundColor: semantic.chart.track }]}>
        <View style={[styles.fill, { backgroundColor: variantColor[variant], width: `${pct}%` }]} />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  row: { gap: spacing[1] },
  header: { flexDirection: 'row', justifyContent: 'space-between' },
  label: { flex: 1, fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  value: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  track: { borderRadius: radius.full, height: 8, overflow: 'hidden' },
  fill: { height: '100%' },
})
