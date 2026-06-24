import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Badge } from '@/components/ui/Badge'
import { ListCell } from '@/components/ui/ListItemPrimitives'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

export interface LineDisplay {
  description: string
  code: string
  quantity: number
  unitPrice: number
  discountAmount: number
  discountPct: number
  subtotal: number
  total: number
}

/** Layout de columnas compartido entre la línea editable de emisión
 * (`DocumentLineRow`) y la línea de solo lectura del detalle de un documento
 * ya emitido — misma presentación, distinta fuente de datos. */
export function DesktopRow({ line }: { line: LineDisplay }) {
  const { semantic } = useTheme()
  return (
    <View style={lineRowStyles.desktopRow}>
      <View style={lineRowStyles.colProduct}>
        <Text style={[lineRowStyles.name, { color: semantic.text.primary }]} numberOfLines={1}>
          {line.description}
        </Text>
        {line.code ? (
          <Text style={[lineRowStyles.code, { color: semantic.text.tertiary }]} numberOfLines={1}>
            {line.code}
          </Text>
        ) : null}
      </View>
      <ListCell label="Cantidad" value={`x${line.quantity}`} style={lineRowStyles.colQuantity} />
      <ListCell
        label="Precio unit."
        value={`$${line.unitPrice.toFixed(2)}`}
        style={lineRowStyles.colUnitPrice}
      />
      <View style={lineRowStyles.colDiscount}>
        <Text style={[lineRowStyles.cellLabel, { color: semantic.text.tertiary }]}>Descuento</Text>
        {line.discountAmount > 0 ? (
          <Badge
            variant="warning"
            size="sm"
            label={`-$${line.discountAmount.toFixed(2)} (${line.discountPct.toFixed(0)}%)`}
          />
        ) : (
          <Text style={[lineRowStyles.cellValue, { color: semantic.text.tertiary }]}>—</Text>
        )}
      </View>
      <ListCell
        label="Sin IVA"
        value={`$${line.subtotal.toFixed(2)}`}
        style={lineRowStyles.colSubtotal}
      />
      <View style={lineRowStyles.colTotal}>
        <Text style={[lineRowStyles.cellLabel, { color: semantic.text.tertiary }]}>Con IVA</Text>
        <Text style={[lineRowStyles.totalValue, { color: semantic.accent.default }]}>
          ${line.total.toFixed(2)}
        </Text>
      </View>
    </View>
  )
}

export function MobileRow({ line }: { line: LineDisplay }) {
  const { semantic } = useTheme()
  return (
    <View style={lineRowStyles.mobileRow}>
      <Text style={[lineRowStyles.name, { color: semantic.text.primary }]} numberOfLines={1}>
        {line.description}
      </Text>
      <Text style={[lineRowStyles.meta, { color: semantic.text.secondary }]} numberOfLines={1}>
        {line.code ? `${line.code} · ` : ''}x{line.quantity} · ${line.unitPrice.toFixed(2)}
      </Text>
      <View style={lineRowStyles.mobileTotalsRow}>
        {line.discountAmount > 0 ? (
          <Badge
            variant="warning"
            size="sm"
            label={`-$${line.discountAmount.toFixed(2)} (${line.discountPct.toFixed(0)}%)`}
          />
        ) : null}
        <Text style={[lineRowStyles.mobileTotals, { color: semantic.text.secondary }]}>
          Sin IVA ${line.subtotal.toFixed(2)}
        </Text>
        <Text style={[lineRowStyles.totalValue, { color: semantic.accent.default }]}>
          ${line.total.toFixed(2)}
        </Text>
      </View>
    </View>
  )
}

export const lineRowStyles = StyleSheet.create({
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
