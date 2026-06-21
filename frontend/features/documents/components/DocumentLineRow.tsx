import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useWatch, type Control } from 'react-hook-form'
import { Badge } from '@/components/ui/Badge'
import { ListCell, ListItemAction } from '@/components/ui/ListItemPrimitives'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { computeLineTotals } from '../form'
import type { EmitDocumentFormValues } from '../schemas'

interface DocumentLineRowProps {
  index: number
  control: Control<EmitDocumentFormValues>
  onPress: () => void
  onRemove: () => void
}

interface LineDisplay {
  description: string
  code: string
  quantity: number
  unitPrice: number
  discountAmount: number
  discountPct: number
  subtotal: number
  total: number
}

/** Fila de una sola línea por producto — pensada para listas largas con muchos items
 * escaneados (lector de código de barras), donde un card expandido por línea
 * sobrecargaría la pantalla. El detalle (cantidad/descuento/IVA/código) se edita en
 * `DocumentLineEditModal`, no inline. */
export function DocumentLineRow({ index, control, onPress, onRemove }: DocumentLineRowProps) {
  const isDesktop = useIsDesktopLayout()
  const { semantic } = useTheme()
  const line = useWatch({ control, name: `lines.${index}` })
  const totals = computeLineTotals(line ? [line] : [])
  const quantity = toNumber(line?.quantity)
  const unitPrice = toNumber(line?.unit_price)
  const discountAmount = toNumber(line?.discount)
  const gross = quantity * unitPrice
  const display: LineDisplay = {
    description: line?.description || 'Producto sin nombre',
    code: line?.code ?? '',
    quantity,
    unitPrice,
    discountAmount,
    discountPct: gross > 0 ? (discountAmount / gross) * 100 : 0,
    subtotal: totals.subtotal,
    total: totals.total,
  }

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`Editar ${display.description}`}
      style={({ pressed }) => [
        styles.row,
        {
          backgroundColor: pressed ? semantic.bg.secondary : semantic.bg.muted,
          borderColor: semantic.border.default,
        },
      ]}
    >
      {isDesktop ? <DesktopRow line={display} /> : <MobileRow line={display} />}
      <ListItemAction
        icon="trash-outline"
        label={`Eliminar ${display.description}`}
        danger
        onPress={onRemove}
      />
    </Pressable>
  )
}

function DesktopRow({ line }: { line: LineDisplay }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.desktopRow}>
      <View style={styles.colProduct}>
        <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
          {line.description}
        </Text>
        {line.code ? (
          <Text style={[styles.code, { color: semantic.text.tertiary }]} numberOfLines={1}>
            {line.code}
          </Text>
        ) : null}
      </View>
      <ListCell label="Cantidad" value={`x${line.quantity}`} style={styles.colQuantity} />
      <ListCell
        label="Precio unit."
        value={`$${line.unitPrice.toFixed(2)}`}
        style={styles.colUnitPrice}
      />
      <View style={styles.colDiscount}>
        <Text style={[styles.cellLabel, { color: semantic.text.tertiary }]}>Descuento</Text>
        {line.discountAmount > 0 ? (
          <Badge
            variant="warning"
            size="sm"
            label={`-$${line.discountAmount.toFixed(2)} (${line.discountPct.toFixed(0)}%)`}
          />
        ) : (
          <Text style={[styles.cellValue, { color: semantic.text.tertiary }]}>—</Text>
        )}
      </View>
      <ListCell label="Sin IVA" value={`$${line.subtotal.toFixed(2)}`} style={styles.colSubtotal} />
      <View style={styles.colTotal}>
        <Text style={[styles.cellLabel, { color: semantic.text.tertiary }]}>Con IVA</Text>
        <Text style={[styles.totalValue, { color: semantic.accent.default }]}>
          ${line.total.toFixed(2)}
        </Text>
      </View>
    </View>
  )
}

function MobileRow({ line }: { line: LineDisplay }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.mobileRow}>
      <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
        {line.description}
      </Text>
      <Text style={[styles.meta, { color: semantic.text.secondary }]} numberOfLines={1}>
        {line.code ? `${line.code} · ` : ''}x{line.quantity} · ${line.unitPrice.toFixed(2)}
      </Text>
      <View style={styles.mobileTotalsRow}>
        {line.discountAmount > 0 ? (
          <Badge
            variant="warning"
            size="sm"
            label={`-$${line.discountAmount.toFixed(2)} (${line.discountPct.toFixed(0)}%)`}
          />
        ) : null}
        <Text style={[styles.mobileTotals, { color: semantic.text.secondary }]}>
          Sin IVA ${line.subtotal.toFixed(2)}
        </Text>
        <Text style={[styles.totalValue, { color: semantic.accent.default }]}>
          ${line.total.toFixed(2)}
        </Text>
      </View>
    </View>
  )
}

function toNumber(value: string | undefined): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    minHeight: 56,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
  },
  desktopRow: {
    alignItems: 'center',
    flex: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    minWidth: 0,
  },
  colProduct: { flex: 1, gap: spacing[1] - 2, minWidth: 160 },
  colQuantity: { flexBasis: 60 },
  colUnitPrice: { flexBasis: 90 },
  colDiscount: { flexBasis: 140, gap: spacing[1] },
  colSubtotal: { flexBasis: 100 },
  colTotal: { flexBasis: 100, gap: spacing[1] },
  name: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  code: { fontSize: typography.size.xs, fontFamily: typography.fontFamily.mono },
  cellLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  cellValue: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  totalValue: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  mobileRow: { flex: 1, gap: spacing[1] - 2, minWidth: 0 },
  meta: { fontSize: typography.size.xs },
  mobileTotalsRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[2],
  },
  mobileTotals: { fontSize: typography.size.xs },
})
