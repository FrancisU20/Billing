import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { RowActionsMenu, type RowAction } from '@/components/ui/RowActionsMenu'
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
    <Pressable
      onPress={onView}
      style={({ pressed }) => [
        styles.container,
        {
          backgroundColor: pressed ? semantic.bg.secondary : semantic.bg.card,
          borderColor: semantic.border.default,
        },
      ]}
    >
      <View style={styles.main}>
        <View style={[styles.icon, { backgroundColor: semantic.accent.subtle }]}>
          <Ionicons name="cube-outline" size={18} color={semantic.accent.default} />
        </View>
        <View style={styles.copy}>
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
        </View>
      </View>
      <View style={styles.actions}>
        <RowActionsMenu actions={rowActions} triggerLabel="Más acciones de producto" />
      </View>
    </Pressable>
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
})
