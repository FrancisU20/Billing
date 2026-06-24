import React from 'react'
import { Pressable } from 'react-native'
import { useWatch, type Control } from 'react-hook-form'
import { ListItemAction } from '@/components/ui/ListItemPrimitives'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import { computeLineTotals } from '../form'
import type { EmitDocumentFormValues } from '../schemas'
import { DesktopRow, lineRowStyles, MobileRow, type LineDisplay } from './LineRowView'

interface DocumentLineRowProps {
  index: number
  control: Control<EmitDocumentFormValues>
  onPress: () => void
  onRemove: () => void
}

/** Fila de una sola línea por producto — pensada para listas largas con muchos items
 * escaneados (lector de código de barras), donde un card expandido por línea
 * sobrecargaría la pantalla. El detalle (cantidad/descuento/IVA/código) se edita en
 * `DocumentLineEditModal`, no inline. La presentación de columnas (desktop/mobile) se
 * comparte con la fila de solo lectura del detalle de un documento ya emitido — ver
 * `LineRowView`. */
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
        lineRowStyles.row,
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

function toNumber(value: string | undefined): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}
