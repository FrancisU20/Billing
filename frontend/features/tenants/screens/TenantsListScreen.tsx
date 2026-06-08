import React, { useMemo, useState } from 'react'
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { TenantListItem } from '../components/TenantListItem'
import {
  TenantsFilters,
  emptyTenantFilterDraft,
  toTenantListFilters,
  type TenantFilterDraft,
} from '../components/TenantsFilters'
import { useTenants } from '../hooks/useTenants'
import type { TenantListFilters } from '../types'

export function TenantsListScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const [draft, setDraft] = useState<TenantFilterDraft>(emptyTenantFilterDraft)
  const [filters, setFilters] = useState<TenantListFilters>({})
  const { tenants, loading, loadingMore, error, refresh, fetchMore } = useTenants(filters)

  const summary = useMemo(() => {
    const active = tenants.filter((tenant) => tenant.status === 'active').length
    const production = tenants.filter((tenant) => tenant.sri_environment === 'production').length
    return { active, production, total: tenants.length }
  }, [tenants])

  function applyFilters() {
    setFilters(toTenantListFilters(draft))
  }

  function resetFilters() {
    setDraft(emptyTenantFilterDraft)
    setFilters({})
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando empresas..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Empresas"
        subtitle={tenants.length ? `${tenants.length} resultados` : 'Administración SaaS'}
      />

      <FlatList
        data={tenants}
        keyExtractor={(tenant) => tenant.id}
        renderItem={({ item }) => (
          <TenantListItem
            tenant={item}
            onView={() => router.push(Routes.superadmin.tenantDetail(item.id) as Href)}
            onEdit={() => router.push(Routes.superadmin.tenantEdit(item.id) as Href)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.heroRow}>
              <View style={styles.heroCopy}>
                <View style={styles.kickerRow}>
                  <Ionicons name="business-outline" size={16} color={semantic.accent.default} />
                  <Text style={[styles.kicker, { color: semantic.accent.default }]}>
                    Empresas registradas
                  </Text>
                </View>
                <Text style={[styles.heading, { color: semantic.text.primary }]}>
                  Tenants, planes y entorno fiscal
                </Text>
              </View>
              <Button
                variant="primary"
                size="md"
                onPress={() => router.push(Routes.superadmin.tenantNew)}
              >
                Nueva empresa
              </Button>
            </View>

            <View style={styles.metricsRow}>
              <Metric label="Activas" value={summary.active} icon="checkmark-circle-outline" />
              <Metric label="Producción" value={summary.production} icon="cloud-done-outline" />
              <Metric label="Cargadas" value={summary.total} icon="layers-outline" />
            </View>

            <TenantsFilters
              value={draft}
              onChange={setDraft}
              onApply={applyFilters}
              onReset={resetFilters}
            />

            {error ? <ApiErrorBanner error={error} /> : null}
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="business-outline"
            title="Sin empresas"
            description="No hay empresas que coincidan con los filtros actuales."
            action={{
              label: 'Crear empresa',
              onPress: () => router.push(Routes.superadmin.tenantNew),
            }}
          />
        }
        ListFooterComponent={
          loadingMore ? (
            <ActivityIndicator color={semantic.accent.default} style={styles.loadingMore} />
          ) : null
        }
        onEndReached={fetchMore}
        onEndReachedThreshold={0.3}
        refreshing={loading}
        onRefresh={refresh}
        showsVerticalScrollIndicator={false}
      />
    </View>
  )
}

function Metric({
  label,
  value,
  icon,
}: {
  label: string
  value: number
  icon: keyof typeof Ionicons.glyphMap
}) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.metric,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={[styles.metricIcon, { backgroundColor: semantic.accent.subtle }]}>
        <Ionicons name={icon} size={16} color={semantic.accent.default} />
      </View>
      <View>
        <Text style={[styles.metricValue, { color: semantic.text.primary }]}>{value}</Text>
        <Text style={[styles.metricLabel, { color: semantic.text.secondary }]}>{label}</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { padding: spacing[4], paddingBottom: spacing[12] },
  header: { gap: spacing[4], marginBottom: spacing[4] },
  heroRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    justifyContent: 'space-between',
  },
  heroCopy: { flex: 1, minWidth: 260, gap: spacing[1] },
  kickerRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[1] },
  kicker: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    textTransform: 'uppercase',
  },
  heading: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * 1.2,
  },
  metricsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  metric: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    minWidth: 150,
    padding: spacing[3],
  },
  metricIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  metricValue: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  metricLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  loadingMore: { paddingVertical: spacing[5] },
})
