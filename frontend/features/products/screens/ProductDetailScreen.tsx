import React, { useState } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { DetailHeader } from '@/components/ui/DetailHeader'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { formatDateTime } from '@/lib/utils/format'
import { Routes } from '@/constants/routes'
import { canWrite } from '@/constants/roles'
import { spacing } from '@/constants/tokens'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { productsApi } from '../api'
import { productKindLabel } from '../constants'
import { ProductStatusBadge } from '../components/ProductStatusBadge'
import { useProduct } from '../hooks/useProduct'

export function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const role = useAuthStore((state) => selectUser(state)?.role ?? null)
  const canManage = canWrite(role)
  const { product, loading, error, refresh } = useProduct(id ?? null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  useRefreshOnFocus(refresh)

  const {
    submitting: deleting,
    error: actionError,
    submit: confirmDelete,
  } = useFormSubmit(async () => {
    if (!id) return
    await productsApi.delete(id, createIdempotencyKey('product_delete'))
    toast.success('Producto eliminado')
    router.replace(Routes.tenant.products as Href)
  })

  if (loading) return <LoadingSpinner fullScreen label="Cargando producto..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Producto" canGoBack />
      {error || !product ? (
        <EmptyState
          icon="alert-circle-outline"
          title="No se pudo cargar el producto"
          description={error?.message ?? 'El producto no existe o no está disponible.'}
          action={{ label: 'Reintentar', onPress: refresh }}
        />
      ) : (
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          {actionError ? <ApiErrorBanner error={actionError} /> : null}

          <DetailHeader
            title={product.name}
            eyebrow={product.sku}
            icon="cube-outline"
            badges={<ProductStatusBadge status={product.status} />}
            actions={
              canManage ? (
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onPress={() => router.push(Routes.tenant.productEdit(product.id) as Href)}
                  >
                    Editar
                  </Button>
                  {product.status === 'ACTIVE' ? (
                    <Button variant="danger" size="sm" onPress={() => setConfirmOpen(true)}>
                      Eliminar
                    </Button>
                  ) : null}
                </>
              ) : null
            }
          />

          <DetailSection title="Datos fiscales" icon="receipt-outline">
            <DetailField label="Tipo" value={productKindLabel(product.kind)} />
            <DetailField label="Descripción" value={product.description || product.name} />
            <DetailField label="IVA" value={product.iva_rate} />
            <DetailField
              label="Precio unitario"
              value={`$${Number(product.unit_price).toFixed(2)}`}
            />
            <DetailField
              label="Descuento"
              value={
                product.discount_percentage
                  ? `${Number(product.discount_percentage)}%`
                  : 'Sin descuento'
              }
            />
            <DetailField label="Unidad" value={product.unit} />
          </DetailSection>

          <DetailSection title="Inventario" icon="layers-outline">
            <DetailField label="Control de stock" value={product.stock_enabled ? 'Sí' : 'No'} />
            <DetailField label="Stock actual" value={product.stock_quantity ?? 'No aplica'} />
            <DetailField label="Umbral bajo" value={product.low_stock_threshold ?? 'No aplica'} />
          </DetailSection>

          <DetailSection title="Metadata" icon="time-outline">
            <DetailField label="Creado" value={formatDateTime(product.created_at)} />
            <DetailField label="Actualizado" value={formatDateTime(product.updated_at)} />
          </DetailSection>
        </ScrollView>
      )}

      <ConfirmDialog
        visible={confirmOpen}
        title="Eliminar producto"
        message={`Se desactivará ${product?.name ?? 'este producto'} y su SKU podrá reutilizarse.`}
        confirmLabel="Eliminar"
        isLoading={deleting}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={confirmDelete}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
})
