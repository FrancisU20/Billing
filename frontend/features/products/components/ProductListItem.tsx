import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ListCell, ListItemAction } from '@/components/ui/ListItemPrimitives'
import { RowActionsMenu, type RowAction } from '@/components/ui/RowActionsMenu'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { productKindLabel } from '../constants'
import type { Product } from '../types'
import { ProductStatusBadge } from './ProductStatusBadge'

interface ProductListItemProps {
  product: Product
  canManage: boolean
  onView: () => void
  onEdit: () => void
  onDelete: () => void
  onToggleStatus: () => void
}

export function ProductListItem({
  product,
  canManage,
  onView,
  onEdit,
  onDelete,
  onToggleStatus,
}: ProductListItemProps) {
  const { semantic } = useTheme()
  const isDesktop = useIsDesktopLayout()
  const stockText = product.stock_enabled
    ? `Stock ${product.stock_quantity ?? '0'}`
    : productKindLabel(product.kind)

  const rowActions: RowAction[] = canManage
    ? [
        { key: 'edit', icon: 'create-outline', label: 'Editar producto', onPress: onEdit },
        product.status === 'ACTIVE'
          ? {
              key: 'delete',
              icon: 'trash-outline',
              label: 'Eliminar producto',
              danger: true,
              onPress: onDelete,
            }
          : {
              key: 'activate',
              icon: 'play-circle-outline',
              label: 'Activar producto',
              onPress: onToggleStatus,
            },
      ]
    : []

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.main}>
        <View style={[styles.icon, { backgroundColor: semantic.accent.subtle }]}>
          <Ionicons name="cube-outline" size={18} color={semantic.accent.default} />
        </View>
        <View style={styles.copy}>
          {isDesktop ? (
            <DesktopRow product={product} stockText={stockText} />
          ) : (
            <MobileRow product={product} stockText={stockText} />
          )}
        </View>
      </View>
      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver producto" onPress={onView} />
        <RowActionsMenu actions={rowActions} triggerLabel="Más acciones de producto" />
      </View>
    </View>
  )
}

function MobileRow({ product, stockText }: { product: Product; stockText: string }) {
  const { semantic } = useTheme()
  return (
    <>
      <View style={styles.titleRow}>
        <Text style={[styles.sku, { color: semantic.text.tertiary }]}>{product.sku}</Text>
        <ProductStatusBadge status={product.status} />
      </View>
      <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
        {product.name}
      </Text>
      <Text style={[styles.meta, { color: semantic.text.secondary }]} numberOfLines={1}>
        {stockText} · IVA {product.iva_rate} · ${Number(product.unit_price).toFixed(2)}
        {product.discount_percentage ? ` · -${Number(product.discount_percentage)}%` : ''}
      </Text>
    </>
  )
}

function DesktopRow({ product, stockText }: { product: Product; stockText: string }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.desktopRow}>
      <View style={styles.colProduct}>
        <View style={styles.titleRow}>
          <Text style={[styles.sku, { color: semantic.text.tertiary }]}>{product.sku}</Text>
          <ProductStatusBadge status={product.status} />
        </View>
        <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
          {product.name}
        </Text>
      </View>
      <ListCell label="Stock / Tipo" value={stockText} style={styles.colKind} />
      <ListCell label="IVA" value={`${product.iva_rate}%`} style={styles.colIva} />
      <ListCell
        label="Precio"
        value={`$${Number(product.unit_price).toFixed(2)}`}
        style={styles.colPrice}
      />
      <ListCell
        label="Descuento"
        value={product.discount_percentage ? `-${Number(product.discount_percentage)}%` : '—'}
        style={styles.colDiscount}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    justifyContent: 'space-between',
    padding: spacing[4],
  },
  main: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: spacing[3], minWidth: 0 },
  icon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  copy: { flex: 1, gap: spacing[1], minWidth: 0 },
  titleRow: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  sku: { fontSize: typography.size.xs, fontWeight: typography.weight.bold },
  name: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  meta: { fontSize: typography.size.sm },
  actions: { flexDirection: 'row', gap: spacing[1] },
  desktopRow: { alignItems: 'center', flex: 1, flexDirection: 'row', gap: spacing[5] },
  colProduct: { flexBasis: 260, gap: spacing[1], minWidth: 200 },
  colKind: { flexBasis: 130 },
  colIva: { flexBasis: 80 },
  colPrice: { flexBasis: 100 },
  colDiscount: { flex: 1, minWidth: 100 },
})
