import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Controller, useWatch, type Control, type FieldErrors } from 'react-hook-form'
import { FormField } from '@/components/ui/FormField'
import { ListItemAction } from '@/components/ui/ListItemPrimitives'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { computeLineTotals } from '../form'
import type { EmitDocumentFormValues } from '../schemas'
import { IvaRatePicker } from './IvaRatePicker'

interface DocumentLineItemProps {
  index: number
  control: Control<EmitDocumentFormValues>
  errors: FieldErrors<EmitDocumentFormValues>
  onChangeIvaRate: (rate: EmitDocumentFormValues['lines'][number]['iva_rate']) => void
  onPickProduct: () => void
  onRemove: () => void
  canRemove: boolean
}

export function DocumentLineItem({
  index,
  control,
  errors,
  onChangeIvaRate,
  onPickProduct,
  onRemove,
  canRemove,
}: DocumentLineItemProps) {
  const { semantic } = useTheme()
  const lineErrors = errors.lines?.[index]
  const line = useWatch({ control, name: `lines.${index}` })
  const totals = computeLineTotals(line ? [line] : [])

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.muted, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Text style={[styles.title, { color: semantic.text.primary }]}>Línea {index + 1}</Text>
          {line?.product_id ? (
            <Text style={[styles.productHint, { color: semantic.accent.default }]}>
              Producto vinculado
            </Text>
          ) : null}
        </View>
        <View style={styles.headerActions}>
          <ListItemAction
            icon="cube-outline"
            label={`Seleccionar producto para línea ${index + 1}`}
            onPress={onPickProduct}
          />
          {canRemove ? (
            <ListItemAction
              icon="trash-outline"
              label={`Eliminar línea ${index + 1}`}
              danger
              onPress={onRemove}
            />
          ) : null}
        </View>
      </View>

      <View style={styles.grid}>
        <View style={styles.col}>
          <Controller
            control={control}
            name={`lines.${index}.code`}
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Código"
                placeholder="P001"
                leftIcon="barcode-outline"
                error={lineErrors?.code?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />
        </View>
        <View style={styles.colWide}>
          <Controller
            control={control}
            name={`lines.${index}.description`}
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Descripción"
                placeholder="Producto o servicio"
                leftIcon="text-outline"
                error={lineErrors?.description?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />
        </View>
      </View>

      <View style={styles.grid}>
        <View style={styles.colSmall}>
          <Controller
            control={control}
            name={`lines.${index}.quantity`}
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Cantidad"
                placeholder="1"
                keyboardType="decimal-pad"
                leftIcon="calculator-outline"
                error={lineErrors?.quantity?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />
        </View>
        <View style={styles.colSmall}>
          <Controller
            control={control}
            name={`lines.${index}.unit_price`}
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Precio unitario"
                placeholder="0.00"
                keyboardType="decimal-pad"
                leftIcon="cash-outline"
                error={lineErrors?.unit_price?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />
        </View>
        <View style={styles.colSmall}>
          <Controller
            control={control}
            name={`lines.${index}.discount`}
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Descuento"
                placeholder="0.00"
                keyboardType="decimal-pad"
                leftIcon="pricetag-outline"
                error={lineErrors?.discount?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
              />
            )}
          />
        </View>
      </View>

      <View style={styles.footerRow}>
        {line ? <IvaRatePicker value={line.iva_rate} onChange={onChangeIvaRate} /> : null}
        <Text style={[styles.lineTotal, { color: semantic.text.primary }]}>
          Total: ${totals.total.toFixed(2)}
        </Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[3] },
  headerRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  headerActions: { flexDirection: 'row', gap: spacing[1] },
  titleBlock: { gap: spacing[1] - 2 },
  title: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  productHint: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  col: { flex: 1, minWidth: 100 },
  colWide: { flex: 2, minWidth: 200 },
  colSmall: { flex: 1, minWidth: 110 },
  footerRow: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    justifyContent: 'space-between',
  },
  lineTotal: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
})
