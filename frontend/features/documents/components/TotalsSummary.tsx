import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

interface TotalsSummaryProps {
  subtotal: number
  totalDiscount: number
  suggestedDiscount?: number
  iva15: number
  iva5: number
  total: number
}

/** Card de totales compartida entre la pantalla de emisión (totales en vivo
 * mientras se arma el documento) y el detalle de un documento ya emitido (totales
 * persistidos). */
export function TotalsSummary({
  subtotal,
  totalDiscount,
  suggestedDiscount,
  iva15,
  iva5,
  total,
}: TotalsSummaryProps) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.totalsCard,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <TotalRow label="Subtotal" value={subtotal} />
      <TotalRow label="Descuento" value={totalDiscount} />
      {suggestedDiscount && suggestedDiscount > 0 ? (
        <TotalRow label="Descuento sugerido" value={suggestedDiscount} muted />
      ) : null}
      <TotalRow label="IVA 15%" value={iva15} />
      <TotalRow label="IVA 5%" value={iva5} />
      <TotalRow label="Total" value={total} emphasis />
    </View>
  )
}

function TotalRow({
  label,
  value,
  emphasis = false,
  muted = false,
}: {
  label: string
  value: number
  emphasis?: boolean
  muted?: boolean
}) {
  const { semantic } = useTheme()
  return (
    <View style={styles.totalRow}>
      <Text
        style={[
          styles.totalLabel,
          emphasis && styles.totalLabelEmphasis,
          {
            color: emphasis
              ? semantic.text.primary
              : muted
                ? semantic.text.tertiary
                : semantic.text.secondary,
          },
        ]}
      >
        {label}
      </Text>
      <Text
        style={[
          styles.totalValue,
          emphasis && styles.totalValueEmphasis,
          { color: semantic.text.primary },
        ]}
      >
        ${value.toFixed(2)}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  totalsCard: { borderRadius: radius.md, borderWidth: 1, gap: spacing[2], padding: spacing[4] },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between' },
  totalLabel: { fontSize: typography.size.sm },
  totalLabelEmphasis: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  totalValue: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  totalValueEmphasis: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
})
