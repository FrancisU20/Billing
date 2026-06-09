import React, { useMemo, useState } from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { plansApi } from '@/features/plans/api'
import { PlanListItem } from '@/features/plans/components/PlanListItem'
import {
  PlansFilters,
  emptyPlanFilterDraft,
  toPlanListFilters,
  type PlanFilterDraft,
} from '@/features/plans/components/PlansFilters'
import { useAdminPlans } from '@/features/plans/hooks/usePlans'
import type { Plan, PlanListFilters } from '@/features/plans/types'

export default function PlansManagementScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [draft, setDraft] = useState<PlanFilterDraft>(emptyPlanFilterDraft)
  const [filters, setFilters] = useState<PlanListFilters>({})
  const [planToToggle, setPlanToToggle] = useState<Plan | null>(null)
  const [toggling, setToggling] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)
  const { plans, loading, error, refresh } = useAdminPlans(filters)

  const summary = useMemo(() => {
    const active = plans.filter((plan) => plan.active).length
    const unlimited = plans.filter((plan) => plan.document_limit === -1).length
    return { active, unlimited, total: plans.length }
  }, [plans])

  function applyFilters() {
    setFilters(toPlanListFilters(draft))
  }

  function resetFilters() {
    setDraft(emptyPlanFilterDraft)
    setFilters({})
  }

  async function confirmToggle() {
    if (!planToToggle) return
    setToggling(true)
    setActionError(null)
    try {
      await plansApi.setStatus(
        planToToggle.id,
        !planToToggle.active,
        createIdempotencyKey('plan_status'),
      )
      toast.success(planToToggle.active ? 'Plan desactivado' : 'Plan activado')
      setPlanToToggle(null)
      await refresh()
    } catch (e) {
      setActionError(toApiError(e))
    } finally {
      setToggling(false)
    }
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando planes..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Planes"
        subtitle={plans.length ? `${plans.length} resultados` : 'Catálogo SaaS'}
      />

      <FlatList
        data={plans}
        keyExtractor={(plan) => plan.id}
        renderItem={({ item }) => (
          <PlanListItem
            plan={item}
            onView={() => router.push(Routes.superadmin.planDetail(item.slug) as Href)}
            onEdit={() => router.push(Routes.superadmin.planEdit(item.slug) as Href)}
            onToggle={() => setPlanToToggle(item)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.heroRow}>
              <View style={styles.heroCopy}>
                <View style={styles.kickerRow}>
                  <Ionicons name="layers-outline" size={16} color={semantic.accent.default} />
                  <Text style={[styles.kicker, { color: semantic.accent.default }]}>
                    Catálogo comercial
                  </Text>
                </View>
                <Text style={[styles.heading, { color: semantic.text.primary }]}>
                  Planes, límites y módulos incluidos
                </Text>
              </View>
              <Button
                variant="primary"
                size="md"
                onPress={() => router.push(Routes.superadmin.planNew)}
              >
                Nuevo plan
              </Button>
            </View>

            <View style={styles.metricsRow}>
              <Metric label="Activos" value={summary.active} icon="checkmark-circle-outline" />
              <Metric label="Ilimitados" value={summary.unlimited} icon="infinite-outline" />
              <Metric label="Cargados" value={summary.total} icon="layers-outline" />
            </View>

            <PlansFilters
              value={draft}
              onChange={setDraft}
              onApply={applyFilters}
              onReset={resetFilters}
            />

            {error ? <ApiErrorBanner error={error} /> : null}
            {actionError ? <ApiErrorBanner error={actionError} /> : null}
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="pricetags-outline"
            title="Sin planes"
            description="No hay planes que coincidan con los filtros actuales."
            action={{ label: 'Crear plan', onPress: () => router.push(Routes.superadmin.planNew) }}
          />
        }
        refreshing={loading}
        onRefresh={refresh}
        showsVerticalScrollIndicator={false}
      />

      <ConfirmDialog
        visible={!!planToToggle}
        title={planToToggle?.active ? 'Desactivar plan' : 'Activar plan'}
        message={`El plan ${planToToggle?.name ?? ''} ${planToToggle?.active ? 'dejará de mostrarse como disponible.' : 'volverá a estar disponible.'}`}
        confirmLabel={planToToggle?.active ? 'Desactivar' : 'Activar'}
        icon={planToToggle?.active ? 'pause-circle-outline' : 'play-circle-outline'}
        isLoading={toggling}
        onCancel={() => setPlanToToggle(null)}
        onConfirm={confirmToggle}
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
})
