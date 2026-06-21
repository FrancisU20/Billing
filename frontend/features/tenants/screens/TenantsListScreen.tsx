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
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { spacing } from '@/constants/tokens'
import { tenantsApi } from '../api'
import { TenantListItem } from '../components/TenantListItem'
import { TenantsFilters } from '../components/TenantsFilters'
import { emptyTenantFilterDraft, toTenantListFilters, type TenantFilterDraft } from '../filters'
import { useTenants } from '../hooks/useTenants'
import type { Tenant, TenantListFilters } from '../types'

export function TenantsListScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [draft, setDraft] = useState<TenantFilterDraft>(emptyTenantFilterDraft)
  const [filters, setFilters] = useState<TenantListFilters>({})
  const [tenantToToggle, setTenantToToggle] = useState<Tenant | null>(null)
  const {
    tenants,
    loading,
    error,
    refresh,
    nextPage,
    previousPage,
    goToPage,
    setPageSize,
    page,
    pageSize,
    totalItems,
    totalPages,
    canGoNext,
    canGoPrevious,
  } = useTenants(filters)
  useRefreshOnFocus(refresh)

  const summary = useMemo(() => {
    const active = tenants.filter((tenant) => tenant.status === 'active').length
    const production = tenants.filter((tenant) => tenant.sri_environment === 'production').length
    return { active, production, total: tenants.length }
  }, [tenants])

  function applyFilters() {
    setFilters(toTenantListFilters(draft))
  }

  const applySearchFilters = useCallback((nextDraft: TenantFilterDraft) => {
    setFilters(toTenantListFilters(nextDraft))
  }, [])

  function resetFilters() {
    setDraft(emptyTenantFilterDraft)
    setFilters({})
  }

  const {
    submitting: togglingStatus,
    error: actionError,
    submit: confirmToggleStatus,
  } = useFormSubmit(async () => {
    if (!tenantToToggle) return
    const nextStatus = tenantToToggle.status === 'active' ? 'suspended' : 'active'
    await tenantsApi.setStatus(tenantToToggle.id, nextStatus, createIdempotencyKey('tenant_status'))
    toast.success(nextStatus === 'active' ? 'Empresa reactivada' : 'Empresa suspendida')
    setTenantToToggle(null)
    await refresh()
  })

  if (loading && tenants.length === 0)
    return <LoadingSpinner fullScreen label="Cargando empresas..." />

  const paginationProps = {
    page,
    pageSize,
    itemCount: tenants.length,
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
        title="Empresas"
        subtitle={
          tenants.length ? `Página ${page} · ${tenants.length} registros` : 'Administración SaaS'
        }
      />

      <FlatList
        data={tenants}
        keyExtractor={(tenant) => tenant.id}
        renderItem={({ item }) => (
          <TenantListItem
            tenant={item}
            onView={() => router.push(Routes.superadmin.tenantDetail(item.id) as Href)}
            onEdit={() => router.push(Routes.superadmin.tenantEdit(item.id) as Href)}
            onToggleStatus={() => setTenantToToggle(item)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <ListScreenHeader
              icon="business-outline"
              kicker="Empresas registradas"
              heading="Tenants, planes y entorno fiscal"
              action={{
                label: 'Nueva empresa',
                onPress: () => router.push(Routes.superadmin.tenantNew),
              }}
            />

            <View style={styles.metricsRow}>
              <StatMetric label="Activas" value={summary.active} icon="checkmark-circle-outline" />
              <StatMetric label="Producción" value={summary.production} icon="cloud-done-outline" />
              <StatMetric label="Cargadas" value={summary.total} icon="layers-outline" />
            </View>

            <TenantsFilters
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
          <View style={styles.paginatorBottom}>
            <ListPaginationControls {...paginationProps} />
          </View>
        }
        refreshing={loading}
        onRefresh={refresh}
        showsVerticalScrollIndicator={false}
      />

      <ConfirmDialog
        visible={!!tenantToToggle}
        title={tenantToToggle?.status === 'active' ? 'Suspender empresa' : 'Reactivar empresa'}
        message={
          tenantToToggle?.status === 'active'
            ? `${tenantToToggle?.trade_name ?? ''} no podrá emitir comprobantes mientras esté suspendida.`
            : `${tenantToToggle?.trade_name ?? ''} volverá a poder emitir comprobantes electrónicos.`
        }
        confirmLabel={tenantToToggle?.status === 'active' ? 'Suspender' : 'Reactivar'}
        icon={tenantToToggle?.status === 'active' ? 'pause-circle-outline' : 'play-circle-outline'}
        isLoading={togglingStatus}
        onCancel={() => setTenantToToggle(null)}
        onConfirm={confirmToggleStatus}
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
