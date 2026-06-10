import React, { useMemo, useState } from 'react'
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native'
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
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { clientsApi } from '../api'
import { ClientListItem } from '../components/ClientListItem'
import {
  ClientsFilters,
  emptyClientFilterDraft,
  toClientListFilters,
  type ClientFilterDraft,
} from '../components/ClientsFilters'
import { useClients } from '../hooks/useClients'
import type { Client, ClientListFilters } from '../types'

export function ClientsListScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [draft, setDraft] = useState<ClientFilterDraft>(emptyClientFilterDraft)
  const [filters, setFilters] = useState<ClientListFilters>({})
  const [clientToDelete, setClientToDelete] = useState<Client | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [actionError, setActionError] = useState<ApiError | null>(null)
  const { clients, loading, loadingMore, error, refresh, fetchMore } = useClients(filters)

  const summary = useMemo(() => {
    const active = clients.filter((client) => client.status === 'active').length
    const inactive = clients.length - active
    return { active, inactive }
  }, [clients])

  function applyFilters() {
    setFilters(toClientListFilters(draft))
  }

  function resetFilters() {
    setDraft(emptyClientFilterDraft)
    setFilters({})
  }

  async function confirmDelete() {
    if (!clientToDelete) return
    setDeleting(true)
    setActionError(null)
    try {
      await clientsApi.delete(clientToDelete.id, createIdempotencyKey('client_delete'))
      toast.success('Cliente eliminado')
      setClientToDelete(null)
      await refresh()
    } catch (e) {
      setActionError(toApiError(e))
    } finally {
      setDeleting(false)
    }
  }

  if (loading) return <LoadingSpinner fullScreen label="Cargando clientes..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Clientes"
        subtitle={clients.length ? `${clients.length} resultados` : 'Facturación Ecuador'}
      />

      <FlatList
        data={clients}
        keyExtractor={(client) => client.id}
        renderItem={({ item }) => (
          <ClientListItem
            client={item}
            onView={() => router.push(Routes.tenant.clientDetail(item.id) as Href)}
            onEdit={() => router.push(Routes.tenant.clientEdit(item.id) as Href)}
            onDelete={() => setClientToDelete(item)}
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
              <Button
                variant="primary"
                size="md"
                onPress={() => router.push(Routes.tenant.clientNew as Href)}
              >
                Nuevo cliente
              </Button>
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
            />

            {error ? <ApiErrorBanner error={error} /> : null}
            {actionError ? <ApiErrorBanner error={actionError} /> : null}
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="people-outline"
            title="Sin clientes"
            description="No hay clientes que coincidan con los filtros actuales."
            action={{
              label: 'Crear cliente',
              onPress: () => router.push(Routes.tenant.clientNew as Href),
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

      <ConfirmDialog
        visible={!!clientToDelete}
        title="Eliminar cliente"
        message={`Se desactivará ${clientToDelete?.trade_name || clientToDelete?.legal_name || 'este cliente'} y su identificación podrá reutilizarse.`}
        confirmLabel="Eliminar"
        isLoading={deleting}
        onCancel={() => setClientToDelete(null)}
        onConfirm={confirmDelete}
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
  loadingMore: { paddingVertical: spacing[5] },
})
