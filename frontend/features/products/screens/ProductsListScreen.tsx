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
import { Input } from '@/components/ui/Input'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { productsApi } from '../api'
import { PRODUCT_KIND_OPTIONS } from '../constants'
import { ProductListItem } from '../components/ProductListItem'
import { useProducts } from '../hooks/useProducts'
import type { Product, ProductKind, ProductListFilters } from '../types'

export function ProductsListScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [q, setQ] = useState('')
  const [kind, setKind] = useState<ProductKind | 'ALL'>('ALL')
  const [filters, setFilters] = useState<ProductListFilters>({})
  const [productToDelete, setProductToDelete] = useState<Product | null>(null)
  const { products, loading, loadingMore, error, refresh, fetchMore } = useProducts(filters)

  const summary = useMemo(() => {
    const active = products.filter((product) => product.status === 'ACTIVE').length
    const stock = products.filter((product) => product.stock_enabled).length
    return { active, stock, total: products.length }
  }, [products])

  function applyFilters() {
    setFilters({
      q: q.trim() || undefined,
      kind: kind === 'ALL' ? undefined : kind,
    })
  }

  function resetFilters() {
    setQ('')
    setKind('ALL')
    setFilters({})
  }

  const {
    submitting: deleting,
    error: actionError,
    submit: confirmDelete,
  } = useFormSubmit(async () => {
    if (!productToDelete) return
    await productsApi.delete(productToDelete.id, createIdempotencyKey('product_delete'))
    toast.success('Producto eliminado')
    setProductToDelete(null)
    await refresh()
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando productos..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar
        title="Productos"
        subtitle={products.length ? `${products.length} resultados` : 'Catálogo facturable'}
      />

      <FlatList
        data={products}
        keyExtractor={(product) => product.id}
        renderItem={({ item }) => (
          <ProductListItem
            product={item}
            onView={() => router.push(Routes.tenant.productDetail(item.id) as Href)}
            onEdit={() => router.push(Routes.tenant.productEdit(item.id) as Href)}
            onDelete={() => setProductToDelete(item)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <View style={styles.heroRow}>
              <View style={styles.heroCopy}>
                <View style={styles.kickerRow}>
                  <Ionicons name="cube-outline" size={16} color={semantic.accent.default} />
                  <Text style={[styles.kicker, { color: semantic.accent.default }]}>Catálogo</Text>
                </View>
                <Text style={[styles.heading, { color: semantic.text.primary }]}>
                  Productos, servicios y membresías para facturar
                </Text>
              </View>
              <Button
                variant="primary"
                size="md"
                onPress={() => router.push(Routes.tenant.productNew as Href)}
              >
                Nuevo producto
              </Button>
            </View>

            <View style={styles.metricsRow}>
              <Metric label="Activos" value={summary.active} icon="checkmark-circle-outline" />
              <Metric label="Con stock" value={summary.stock} icon="layers-outline" />
              <Metric label="Cargados" value={summary.total} icon="cube-outline" />
            </View>

            <View
              style={[
                styles.filters,
                { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
              ]}
            >
              <Input
                value={q}
                onChangeText={setQ}
                placeholder="Buscar por SKU, nombre o descripción"
                leftIcon="search-outline"
              />
              <SegmentedControl
                value={kind}
                options={[
                  { value: 'ALL', label: 'Todos' },
                  ...PRODUCT_KIND_OPTIONS.map((option) => ({
                    value: option.value,
                    label: option.label,
                  })),
                ]}
                onChange={(next) => setKind(next)}
              />
              <View style={styles.filterActions}>
                <Button variant="outline" size="sm" onPress={resetFilters}>
                  Limpiar
                </Button>
                <Button variant="secondary" size="sm" onPress={applyFilters}>
                  Aplicar
                </Button>
              </View>
            </View>

            {error ? <ApiErrorBanner error={error} /> : null}
            {actionError ? <ApiErrorBanner error={actionError} /> : null}
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="cube-outline"
            title="Sin productos"
            description="Crea tu primer producto o servicio para usarlo en el facturador."
            action={{
              label: 'Crear producto',
              onPress: () => router.push(Routes.tenant.productNew as Href),
            }}
          />
        }
        ListFooterComponent={
          loadingMore ? (
            <View style={styles.loadingMore}>
              <LoadingSpinner size="small" compact />
            </View>
          ) : null
        }
        onEndReached={fetchMore}
        onEndReachedThreshold={0.3}
        refreshing={loading}
        onRefresh={refresh}
        showsVerticalScrollIndicator={false}
      />

      <ConfirmDialog
        visible={!!productToDelete}
        title="Eliminar producto"
        message={`Se eliminará ${productToDelete?.name || 'este producto'} del catálogo. Las facturas emitidas conservarán su snapshot.`}
        confirmLabel="Eliminar"
        isLoading={deleting}
        onCancel={() => setProductToDelete(null)}
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
  filters: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[3] },
  filterActions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  loadingMore: { paddingVertical: spacing[5] },
})
