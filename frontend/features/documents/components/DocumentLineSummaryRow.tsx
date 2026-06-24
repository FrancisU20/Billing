import React from 'react'
import { View } from 'react-native'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import type { DocumentLine } from '../schemas'
import { DesktopRow, lineRowStyles, MobileRow, type LineDisplay } from './LineRowView'

/** Fila de solo lectura para una línea de un documento ya emitido — misma
 * presentación de columnas que `DocumentLineRow` (emisión), sin acción de editar
 * ni eliminar, y usando los montos ya calculados que persiste el documento. */
export function DocumentLineSummaryRow({ line }: { line: DocumentLine }) {
  const isDesktop = useIsDesktopLayout()
  const { semantic } = useTheme()
  const quantity = Number(line.quantity)
  const unitPrice = Number(line.unit_price)
  const discountAmount = Number(line.discount)
  const gross = quantity * unitPrice
  const display: LineDisplay = {
    description: line.description,
    code: line.code,
    quantity,
    unitPrice,
    discountAmount,
    discountPct: gross > 0 ? (discountAmount / gross) * 100 : 0,
    subtotal: Number(line.subtotal),
    total: Number(line.total),
  }

  return (
    <View
      style={[
        lineRowStyles.row,
        { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
      ]}
    >
      {isDesktop ? <DesktopRow line={display} /> : <MobileRow line={display} />}
    </View>
  )
}
