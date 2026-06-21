import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { radius, sizes, spacing, typography } from '@/constants/tokens'

interface StatMetricTrend {
  /** % de variacion vs el periodo anterior. Omitir el prop `trend` entero (no pasar
   * `pct: null`) cuando no hay base honesta para comparar — ver `GetSuperadminDashboardUseCase`. */
  pct: number
  label: string
}

interface StatMetricProps {
  label: string
  /** Numero crudo (conteos) o string ya formateado (ej. moneda via `formatCurrency`). */
  value: number | string
  icon: keyof typeof Ionicons.glyphMap
  trend?: StatMetricTrend
  /** `lg` para metricas destacadas (ej. ingresos/MRR) — icono, valor y padding mas grandes. */
  size?: 'md' | 'lg'
}

export function StatMetric({ label, value, icon, trend, size = 'md' }: StatMetricProps) {
  const { semantic } = useTheme()
  const trendUp = (trend?.pct ?? 0) >= 0
  const trendColor = trendUp ? semantic.status.success : semantic.status.error
  const isLarge = size === 'lg'

  return (
    <View
      style={[
        styles.metric,
        isLarge && styles.metricLarge,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View
        style={[
          styles.metricIcon,
          isLarge && styles.metricIconLarge,
          { backgroundColor: semantic.accent.subtle },
        ]}
      >
        <Ionicons name={icon} size={isLarge ? 22 : 16} color={semantic.accent.default} />
      </View>
      <View style={styles.metricCopy}>
        <Text
          style={[
            styles.metricValue,
            isLarge && styles.metricValueLarge,
            { color: semantic.text.primary },
          ]}
        >
          {value}
        </Text>
        <Text style={[styles.metricLabel, { color: semantic.text.secondary }]}>{label}</Text>
        {trend ? (
          <View style={styles.trendRow}>
            <Ionicons
              name={trendUp ? 'arrow-up-outline' : 'arrow-down-outline'}
              size={11}
              color={trendColor}
            />
            <Text style={[styles.trendText, { color: trendColor }]} numberOfLines={1}>
              {Math.abs(trend.pct)}% {trend.label}
            </Text>
          </View>
        ) : null}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  metric: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    minWidth: 150,
    padding: spacing[3],
  },
  metricLarge: { minWidth: 220, padding: spacing[4] },
  metricIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  metricIconLarge: { height: sizes.icon + 12, width: sizes.icon + 12 },
  metricCopy: { minWidth: 0 },
  metricValue: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  metricValueLarge: { fontSize: typography.size['2xl'] },
  metricLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  trendRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[1], marginTop: spacing[1] },
  trendText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
})
