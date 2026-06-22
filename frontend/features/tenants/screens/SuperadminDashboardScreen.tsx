import React from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useRouter, type Href } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { EntityAvatar } from '@/components/ui/ListItemPrimitives'
import { ListScreenHeader } from '@/components/layout/ListScreenHeader'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { StatMetric } from '@/components/ui/StatMetric'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { formatCurrency, formatDateTime, formatRelativeTime, initials } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
import { Routes } from '@/constants/routes'
import { TENANT_ENVIRONMENT_BADGE_VARIANT } from '../constants'
import { DistributionBar } from '../components/DistributionBar'
import { TrendChart } from '../components/TrendChart'
import { useSuperadminDashboard } from '../hooks/useSuperadminDashboard'

export function SuperadminDashboardScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const { summary, loading, error, refresh } = useSuperadminDashboard()
  useRefreshOnFocus(refresh)

  if (loading && !summary) return <LoadingSpinner fullScreen label="Cargando estadísticas..." />

  const tenantsByEnvironment = summary?.tenants_by_environment ?? {}
  const tenantsTotal = summary?.tenants_total ?? 0
  const membershipsActive = summary?.memberships_active ?? 0
  const membershipsInactive = summary?.memberships_inactive ?? 0

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Dashboard"
        subtitle={summary ? `Actualizado ${formatDateTime(summary.generated_at)}` : 'Panel global'}
      />

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <ListScreenHeader
          icon="analytics-outline"
          kicker="Panel global"
          heading="Estadísticas de la plataforma"
        />

        {error ? <ApiErrorBanner error={error} /> : null}

        <View style={styles.metricsGrid}>
          <View style={styles.metricsGridItem}>
            <StatMetric label="Tenants registrados" value={tenantsTotal} icon="business-outline" />
          </View>
          <View style={styles.metricsGridItem}>
            <StatMetric
              label="Nuevos este mes"
              value={summary?.tenants_new_this_month ?? 0}
              icon="sparkles-outline"
              trend={trendProp(summary?.tenants_new_this_month_trend_pct, 'vs. mes anterior')}
            />
          </View>
          <View style={styles.metricsGridItem}>
            <StatMetric
              label="Membresías activas"
              value={membershipsActive}
              icon="checkmark-circle-outline"
            />
          </View>
          <View style={styles.metricsGridItem}>
            <StatMetric
              label="Membresías inactivas"
              value={membershipsInactive}
              icon="pause-circle-outline"
            />
          </View>
        </View>

        <View style={styles.revenueMetricsGrid}>
          <View style={styles.revenueMetricItem}>
            <StatMetric
              size="lg"
              label="Ingresos del mes"
              value={formatCurrency(summary?.revenue_this_month ?? '0.00')}
              icon="cash-outline"
              trend={trendProp(summary?.revenue_this_month_trend_pct, 'vs. mes anterior')}
            />
          </View>
          <View style={styles.revenueMetricItem}>
            <StatMetric
              size="lg"
              label="Ingresos del año"
              value={formatCurrency(summary?.revenue_this_year ?? '0.00')}
              icon="trending-up-outline"
              trend={trendProp(summary?.revenue_this_year_trend_pct, 'vs. año anterior')}
            />
          </View>
          <View style={styles.revenueMetricItem}>
            <StatMetric
              size="lg"
              label="MRR estimado"
              value={formatCurrency(summary?.mrr_estimate ?? '0.00')}
              icon="repeat-outline"
            />
          </View>
        </View>

        <View style={styles.twoColumnRow}>
          <Card variant="elevated" elevated style={[styles.chartCard, styles.columnCard]}>
            <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>
              Evolución de ingresos (últimos 30 días)
            </Text>
            <TrendChart
              data={(summary?.daily_revenue ?? []).map((point) => ({
                date: point.date,
                value: Number(point.amount),
              }))}
            />
          </Card>

          <Card variant="elevated" elevated style={[styles.distributionCard, styles.columnCard]}>
            <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>
              Estado de la plataforma
            </Text>
            <DistributionBar
              label="En producción"
              count={tenantsByEnvironment.production ?? 0}
              total={tenantsTotal}
              variant={TENANT_ENVIRONMENT_BADGE_VARIANT.production}
            />
            <DistributionBar
              label="En pruebas"
              count={tenantsByEnvironment.testing ?? 0}
              total={tenantsTotal}
              variant={TENANT_ENVIRONMENT_BADGE_VARIANT.testing}
            />
            <DistributionBar
              label="Membresías activas"
              count={membershipsActive}
              total={tenantsTotal}
              variant="success"
            />
            <DistributionBar
              label="Membresías inactivas"
              count={membershipsInactive}
              total={tenantsTotal}
              variant="error"
            />
          </Card>
        </View>

        <Card variant="elevated" elevated style={styles.insightCard}>
          <View style={styles.insightHeader}>
            <View style={[styles.insightIcon, { backgroundColor: semantic.accent.subtle }]}>
              <Ionicons name="trophy-outline" size={20} color={semantic.accent.default} />
            </View>
            <View style={styles.insightCopy}>
              <Text style={[styles.insightTitle, { color: semantic.text.primary }]}>
                Plan más vendido
              </Text>
              <Text style={[styles.insightDescription, { color: semantic.text.secondary }]}>
                {summary?.top_plan
                  ? `${summary.top_plan.name} — ${summary.top_plan.tenant_count} tenant${summary.top_plan.tenant_count === 1 ? '' : 's'} con membresía activa.`
                  : 'Todavía no hay tenants con membresía activa.'}
              </Text>
            </View>
            {summary?.top_plan ? (
              <Badge label="#1 Más popular" variant="primary" size="sm" />
            ) : null}
          </View>
        </Card>

        <Card variant="elevated" elevated style={styles.insightCard}>
          <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>
            Tenants recientes
          </Text>
          {summary?.recent_tenants.length ? (
            summary.recent_tenants.map((tenant) => (
              <Pressable
                key={tenant.id}
                style={styles.recentRow}
                onPress={() => router.push(Routes.superadmin.tenantDetail(tenant.id) as Href)}
              >
                <EntityAvatar initials={initials(tenant.trade_name)} />
                <Text
                  style={[styles.recentName, { color: semantic.text.primary }]}
                  numberOfLines={1}
                >
                  {tenant.trade_name}
                </Text>
                <Text style={[styles.recentTime, { color: semantic.text.secondary }]}>
                  {formatRelativeTime(tenant.created_at)}
                </Text>
              </Pressable>
            ))
          ) : (
            <Text style={[styles.insightDescription, { color: semantic.text.secondary }]}>
              Todavía no hay tenants registrados.
            </Text>
          )}
        </Card>
      </ScrollView>
    </View>
  )
}

function trendProp(pct: number | null | undefined, label: string) {
  return pct === null || pct === undefined ? undefined : { pct, label }
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: spacing[5], gap: spacing[5], paddingBottom: spacing[12] },
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  metricsGridItem: { flex: 1, minWidth: 180 },
  revenueMetricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  revenueMetricItem: { flex: 1, minWidth: 220 },
  sectionTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  twoColumnRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[5] },
  columnCard: { flex: 1, minWidth: 320 },
  distributionCard: { gap: spacing[3] },
  chartCard: { gap: spacing[3] },
  insightCard: { gap: spacing[4] },
  insightHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  insightIcon: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  insightCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  insightTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  insightDescription: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
  },
  recentRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  recentName: { flex: 1, fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  recentTime: { fontSize: typography.size.xs },
})
