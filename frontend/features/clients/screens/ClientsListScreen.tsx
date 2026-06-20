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
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { canWrite } from '@/constants/roles'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { clientsApi } from '../api'
import { ClientListItem } from '../components/ClientListItem'
import { ClientsFilters } from '../components/ClientsFilters'
import { emptyClientFilterDraft, toClientListFilters, type ClientFilterDraft } from '../filters'
import { useClients } from '../hooks/useClients'
import type { Client, ClientListFilters } from '../types'

export function ClientsListScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const role = useAuthStore((state) => selectUser(state)?.role ?? null)
  const canManage = canWrite(role)
  const [draft, setDraft] = useState<ClientFilterDraft>(emptyClientFilterDraft)
  const [filters, setFilters] = useState<ClientListFilters>({})
  const [clientToDelete, setClientToDelete] = useState<Client | null>(null)
  const [clientToToggle, setClientToToggle] = useState<Client | null>(null)
  const {
    clients,
    loading,
    error,
    refresh,
    nextPage,
    previousPage,
    setPageSize,
    page,
    pageSize,
    totalItems,
    totalPages,
    canGoNext,
    canGoPrevious,
  } = useClients(filters)
  useRefreshOnFocus(refresh)

  const summary = useMemo(() => {
    const active = clients.filter((client) => client.status === 'active').length
    const inactive = clients.length - active
    return { active, inactive }
  }, [clients])

  function applyFilters() {
    setFilters(toClientListFilters(draft))
  }

  const applySearchFilters = useCallback((nextDraft: ClientFilterDraft) => {
    setFilters(toClientListFilters(nextDraft))
  }, [])

  function resetFilters() {
    setDraft(emptyClientFilterDraft)
    setFilters({})
  }

  const {
    submitting: deleting,
    error: actionError,
    submit: confirmDelete,
  } = useFormSubmit(async () => {
    if (!clientToDelete) return
    await clientsApi.delete(clientToDelete.id, createIdempotencyKey('client_delete'))
    toast.success('Cliente eliminado')
    setClientToDelete(null)
    await refresh()
  })

  const {
    submitting: activating,
    error: toggleError,
    submit: confirmActivate,
  } = useFormSubmit(async () => {
    if (!clientToToggle) return
    await clientsApi.setStatus(clientToToggle.id, 'active', createIdempotencyKey('client_status'))
    toast.success('Cliente activado')
    setClientToToggle(null)
    await refresh()
  })

  if (loading && clients.length === 0)
    return <LoadingSpinner fullScreen label="Cargando clientes..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Clientes"
        subtitle={
          clients.length ? `Página ${page} · ${clients.length} registros` : 'Facturación Ecuador'
        }
      />

      <FlatList
        data={clients}
        keyExtractor={(client) => client.id}
        renderItem={({ item }) => (
          <ClientListItem
            client={item}
            canManage={canManage}
            onView={() => router.push(Routes.tenant.clientDetail(item.id) as Href)}
            onEdit={() => router.push(Routes.tenant.clientEdit(item.id) as Href)}
            onDelete={() => setClientToDelete(item)}
            onToggleStatus={() => setClientToToggle(item)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.heroRow}>
              <View style={styles.heroCopy}>
                <View style={styles.kickerRow}>
                  <Ionicons name="people-outline" size={16} color={semantic.accent.default} />
                  <Text style={[styles.kicker, { color: semantic.accent.default }]}>
                    Cartera de clientes
                  </Text>
                </View>
                <Text style={[styles.heading, { color: semantic.text.primary }]}>
                  Clientes para emisión y control fiscal
                </Text>
              </View>
              {canManage ? (
                <Button
                  variant="primary"
                  size="md"
                  onPress={() => router.push(Routes.tenant.clientNew as Href)}
                >
                  Nuevo cliente
                </Button>
              ) : null}
            </View>

            <View style={styles.metricsRow}>
              <Metric label="Activos" value={summary.active} icon="checkmark-circle-outline" />
              <Metric label="Inactivos" value={summary.inactive} icon="pause-circle-outline" />
              <Metric label="Cargados" value={clients.length} icon="layers-outline" />
            </View>

            <ClientsFilters
              value={draft}
              onChange={setDraft}
              onApply={applyFilters}
              onReset={resetFilters}
              onSearchApply={applySearchFilters}
            />

            {error ? <ApiErrorBanner error={error} /> : null}
            {actionError ? <ApiErrorBanner error={actionError} /> : null}
            {toggleError ? <ApiErrorBanner error={toggleError} /> : null}
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="people-outline"
            title="Sin clientes"
            description="No hay clientes que coincidan con los filtros actuales."
            action={
              canManage
                ? {
                    label: 'Crear cliente',
                    onPress: () => router.push(Routes.tenant.clientNew as Href),
                  }
                : undefined
            }
          />
        }
        ListFooterComponent={
          <ListPaginationControls
            page={page}
            pageSize={pageSize}
            itemCount={clients.length}
            totalItems={totalItems}
            totalPages={totalPages}
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
        visible={!!clientToDelete}
        title="Eliminar cliente"
        message={`Se desactivará ${clientToDelete?.trade_name || clientToDelete?.legal_name || 'este cliente'} y su identificación podrá reutilizarse.`}
        confirmLabel="Eliminar"
        isLoading={deleting}
        onCancel={() => setClientToDelete(null)}
        onConfirm={confirmDelete}
      />

      <ConfirmDialog
        visible={!!clientToToggle}
        title="Activar cliente"
        message={`${clientToToggle?.trade_name || clientToToggle?.legal_name || 'Este cliente'} volverá a estar disponible para facturación.`}
        confirmLabel="Activar"
        icon="play-circle-outline"
        isLoading={activating}
        onCancel={() => setClientToToggle(null)}
        onConfirm={confirmActivate}
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
