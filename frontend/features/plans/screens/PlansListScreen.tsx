import React, { useCallback, useMemo, useState } from 'react'
import { FlatList, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { ListPaginationControls } from '@/components/ui/ListPaginationControls'
import { ListScreenHeader } from '@/components/layout/ListScreenHeader'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { StatMetric } from '@/components/ui/StatMetric'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useLocalPagedItems } from '@/lib/hooks/useLocalPagedItems'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
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
    totalItems,
    totalPages,
    canGoNext,
    canGoPrevious,
    nextPage,
    previousPage,
    goToPage,
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

  const paginationProps = {
    page,
    pageSize,
    itemCount: visiblePlans.length,
    totalItems,
    totalPages,
    onGoToPage: goToPage,
    canGoPrevious,
    canGoNext,
    loading,
    onPrevious: previousPage,
    onNext: nextPage,
    onPageSizeChange: setPageSize,
  }

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
            <ListScreenHeader
              icon="layers-outline"
              kicker="Catálogo comercial"
              heading="Planes, límites y módulos incluidos"
              action={{
                label: 'Nuevo plan',
                onPress: () => router.push(Routes.superadmin.planNew),
              }}
            />

            <View style={styles.metricsRow}>
              <StatMetric label="Activos" value={summary.active} icon="checkmark-circle-outline" />
              <StatMetric label="Ilimitados" value={summary.unlimited} icon="infinite-outline" />
              <StatMetric label="Cargados" value={summary.total} icon="layers-outline" />
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

            <ListPaginationControls {...paginationProps} />
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
          <View style={styles.paginatorBottom}>
            <ListPaginationControls {...paginationProps} />
          </View>
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

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { padding: spacing[4], paddingBottom: spacing[12] },
  header: { gap: spacing[4], marginBottom: spacing[4] },
  paginatorBottom: { marginTop: spacing[4] },
  metricsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
})
