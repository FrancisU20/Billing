import React from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { Button } from '@/components/ui/Button'
import { DetailField, DetailSection } from '@/components/ui/DetailSection'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useTheme } from '@/lib/theme-context'
import { formatDateTime } from '@/lib/utils/format'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { productKindLabel } from '../constants'
import { ProductStatusBadge } from '../components/ProductStatusBadge'
import { useProduct } from '../hooks/useProduct'

export function ProductDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const { semantic } = useTheme()
  const { product, loading, error, refresh } = useProduct(id ?? null)

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
          <View
            style={[
              styles.header,
              { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
            ]}
          >
            <View style={[styles.icon, { backgroundColor: semantic.accent.subtle }]}>
              <Ionicons name="cube-outline" size={22} color={semantic.accent.default} />
            </View>
            <View style={styles.headerCopy}>
              <Text style={[styles.sku, { color: semantic.text.tertiary }]}>{product.sku}</Text>
              <Text style={[styles.title, { color: semantic.text.primary }]}>{product.name}</Text>
              <ProductStatusBadge status={product.status} />
            </View>
            <Button
              variant="secondary"
              size="sm"
              onPress={() => router.push(Routes.tenant.productEdit(product.id) as Href)}
            >
              Editar
            </Button>
          </View>

          <DetailSection title="Datos fiscales" icon="receipt-outline">
            <DetailField label="Tipo" value={productKindLabel(product.kind)} />
            <DetailField label="Descripción" value={product.description || product.name} />
            <DetailField label="IVA" value={product.iva_rate} />
            <DetailField
              label="Precio unitario"
              value={`$${Number(product.unit_price).toFixed(2)}`}
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
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  header: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    padding: spacing[4],
  },
  icon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 48,
    justifyContent: 'center',
    width: 48,
  },
  headerCopy: { flex: 1, gap: spacing[1], minWidth: 220 },
  sku: { fontSize: typography.size.xs, fontWeight: typography.weight.bold },
  title: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
})
