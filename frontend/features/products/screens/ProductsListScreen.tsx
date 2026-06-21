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
import { canWrite } from '@/constants/roles'
import { spacing } from '@/constants/tokens'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { productsApi } from '../api'
import { ProductListItem } from '../components/ProductListItem'
import { ProductsFilters } from '../components/ProductsFilters'
import { emptyProductFilterDraft, toProductListFilters, type ProductFilterDraft } from '../filters'
import { useProducts } from '../hooks/useProducts'
import type { Product, ProductListFilters } from '../types'

export function ProductsListScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const role = useAuthStore((state) => selectUser(state)?.role ?? null)
  const canManage = canWrite(role)
  const [draft, setDraft] = useState<ProductFilterDraft>(emptyProductFilterDraft)
  const [filters, setFilters] = useState<ProductListFilters>({})
  const [productToDelete, setProductToDelete] = useState<Product | null>(null)
  const [productToToggle, setProductToToggle] = useState<Product | null>(null)
  const {
    products,
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
  } = useProducts(filters)
  useRefreshOnFocus(refresh)

  const summary = useMemo(() => {
    const active = products.filter((product) => product.status === 'ACTIVE').length
    const stock = products.filter((product) => product.stock_enabled).length
    return { active, stock, total: products.length }
  }, [products])

  function applyFilters() {
    setFilters(toProductListFilters(draft))
  }

  const applySearchFilters = useCallback((nextDraft: ProductFilterDraft) => {
    setFilters(toProductListFilters(nextDraft))
  }, [])

  function resetFilters() {
    setDraft(emptyProductFilterDraft)
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

  const {
    submitting: activating,
    error: toggleError,
    submit: confirmActivate,
  } = useFormSubmit(async () => {
    if (!productToToggle) return
    await productsApi.setStatus(
      productToToggle.id,
      'ACTIVE',
      createIdempotencyKey('product_status'),
    )
    toast.success('Producto activado')
    setProductToToggle(null)
    await refresh()
  })

  if (loading && products.length === 0) {
    return <LoadingSpinner fullScreen label="Cargando productos..." />
  }

  const paginationProps = {
    page,
    pageSize,
    itemCount: products.length,
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
        title="Productos"
        subtitle={
          products.length ? `Página ${page} · ${products.length} registros` : 'Catálogo facturable'
        }
      />

      <FlatList
        data={products}
        keyExtractor={(product) => product.id}
        renderItem={({ item }) => (
          <ProductListItem
            product={item}
            canManage={canManage}
            onView={() => router.push(Routes.tenant.productDetail(item.id) as Href)}
            onEdit={() => router.push(Routes.tenant.productEdit(item.id) as Href)}
            onDelete={() => setProductToDelete(item)}
            onToggleStatus={() => setProductToToggle(item)}
          />
        )}
        contentContainerStyle={styles.list}
        ListHeaderComponent={
          <View style={styles.header}>
            <ListScreenHeader
              icon="cube-outline"
              kicker="Catálogo"
              heading="Productos, servicios y membresías para facturar"
              action={
                canManage
                  ? {
                      label: 'Nuevo producto',
                      onPress: () => router.push(Routes.tenant.productNew as Href),
                    }
                  : undefined
              }
            />

            <View style={styles.metricsRow}>
              <StatMetric label="Activos" value={summary.active} icon="checkmark-circle-outline" />
              <StatMetric label="Con stock" value={summary.stock} icon="layers-outline" />
              <StatMetric label="Cargados" value={summary.total} icon="cube-outline" />
            </View>

            <ProductsFilters
              value={draft}
              onChange={setDraft}
              onApply={applyFilters}
              onReset={resetFilters}
              onSearchApply={applySearchFilters}
            />

            {error ? <ApiErrorBanner error={error} /> : null}
            {actionError ? <ApiErrorBanner error={actionError} /> : null}
            {toggleError ? <ApiErrorBanner error={toggleError} /> : null}

            <ListPaginationControls {...paginationProps} />
          </View>
        }
        ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
        ListEmptyComponent={
          <EmptyState
            icon="cube-outline"
            title="Sin productos"
            description="Crea tu primer producto o servicio para usarlo en el facturador."
            action={
              canManage
                ? {
                    label: 'Crear producto',
                    onPress: () => router.push(Routes.tenant.productNew as Href),
                  }
                : undefined
            }
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
        visible={!!productToDelete}
        title="Eliminar producto"
        message={`Se eliminará ${productToDelete?.name || 'este producto'} del catálogo. Las facturas emitidas conservarán su snapshot.`}
        confirmLabel="Eliminar"
        isLoading={deleting}
        onCancel={() => setProductToDelete(null)}
        onConfirm={confirmDelete}
      />

      <ConfirmDialog
        visible={!!productToToggle}
        title="Activar producto"
        message={`${productToToggle?.name || 'Este producto'} volverá a estar disponible para facturación.`}
        confirmLabel="Activar"
        icon="play-circle-outline"
        isLoading={activating}
        onCancel={() => setProductToToggle(null)}
        onConfirm={confirmActivate}
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
