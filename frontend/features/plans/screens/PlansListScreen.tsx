import React, { useCallback, useMemo, useState } from 'react'
import { FlatList, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { ListPaginationControls } from '@/components/ui/ListPaginationControls'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useLocalPagedItems } from '@/lib/hooks/useLocalPagedItems'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { plansApi } from '../api'
import { PlanListItem } from '../components/PlanListItem'
import { PlansFilters } from '../components/PlansFilters'
import { emptyPlanFilterDraft, toPlanListFilters, type PlanFilterDraft } from '../filters'
import { useAdminPlans } from '../hooks/usePlans'
import type { Plan, PlanListFilters } from '../types'

export function PlansListScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [draft, setDraft] = useState<PlanFilterDraft>(emptyPlanFilterDraft)
  const [filters, setFilters] = useState<PlanListFilters>({})
  const [planToToggle, setPlanToToggle] = useState<Plan | null>(null)
  const { plans, loading, error, refresh } = useAdminPlans(filters)
  const {
    pageItems: visiblePlans,
    page,
    pageSize,
    totalPages,
    canGoNext,
    canGoPrevious,
    nextPage,
    previousPage,
    setPageSize,
  } = useLocalPagedItems(plans)
  useRefreshOnFocus(refresh)

  const summary = useMemo(() => {
    const active = plans.filter((plan) => plan.active).length
    const unlimited = plans.filter((plan) => plan.document_limit === -1).length
    return { active, unlimited, total: plans.length }
  }, [plans])

  function applyFilters() {
    setFilters(toPlanListFilters(draft))
  }

  const applySearchFilters = useCallback((nextDraft: PlanFilterDraft) => {
    setFilters(toPlanListFilters(nextDraft))
  }, [])

  function resetFilters() {
    setDraft(emptyPlanFilterDraft)
    setFilters({})
  }

  const {
    submitting: toggling,
    error: actionError,
    submit: confirmToggle,
  } = useFormSubmit(async () => {
    if (!planToToggle) return
    await plansApi.setStatus(
      planToToggle.id,
      !planToToggle.active,
      createIdempotencyKey('plan_status'),
    )
    toast.success(planToToggle.active ? 'Plan desactivado' : 'Plan activado')
    setPlanToToggle(null)
    await refresh()
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando planes..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Planes"
        subtitle={
          plans.length
            ? `Página ${page} de ${totalPages} · ${plans.length} planes`
            : 'Catálogo SaaS'
        }
      />

      <FlatList
        data={visiblePlans}
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
              onSearchApply={applySearchFilters}
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
        ListFooterComponent={
          <ListPaginationControls
            page={page}
            pageSize={pageSize}
            itemCount={visiblePlans.length}
            canGoPrevious={canGoPrevious}
            canGoNext={canGoNext}
            loading={loading}
            onPrevious={previousPage}
            onNext={nextPage}
            onPageSizeChange={setPageSize}
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
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  metricValue: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  metricLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
})
