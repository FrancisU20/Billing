import React from 'react'
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Controller, useWatch, type Control, type FieldErrors } from 'react-hook-form'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { DiscountInput } from '@/components/ui/DiscountInput'
import { FormField } from '@/components/ui/FormField'
import { MoneyField } from '@/components/ui/SpecializedFields'
import { useTheme } from '@/lib/theme-context'
import { overlay, radius, spacing, typography } from '@/constants/tokens'
import { computeLineTotals, resolveDiscountPolicy } from '../form'
import type { EmitDocumentFormValues } from '../schemas'
import { IvaRatePicker } from './IvaRatePicker'

interface DocumentLineEditModalProps {
  index: number | null
  control: Control<EmitDocumentFormValues>
  errors: FieldErrors<EmitDocumentFormValues>
  onChangeIvaRate: (rate: EmitDocumentFormValues['lines'][number]['iva_rate']) => void
  onClose: () => void
  productDiscountPercentage?: string | null
  campaign?: { active: boolean; percentage: string } | null
}

/** Detalle editable de una línea (cantidad/descuento/IVA/código/descripción), separado
 * de la fila compacta de la lista — ver `DocumentLineRow`. */
export function DocumentLineEditModal({
  index,
  control,
  errors,
  onChangeIvaRate,
  onClose,
  productDiscountPercentage = null,
  campaign = null,
}: DocumentLineEditModalProps) {
  const { semantic } = useTheme()
  const visible = index !== null
  const safeIndex = index ?? 0
  const lineErrors = errors.lines?.[safeIndex]
  const line = useWatch({ control, name: `lines.${safeIndex}` })
  const totals = computeLineTotals(line && visible ? [line] : [])
  const discountBase = line && visible ? toNumber(line.quantity) * toNumber(line.unit_price) : 0
  const discountPolicy =
    line && visible
      ? resolveDiscountPolicy(line.quantity, line.unit_price, productDiscountPercentage, campaign)
      : null
  const appliedDiscount = toNumber(line?.discount)
  const suggestedDiscount = toNumber(discountPolicy?.amount)

  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View
          style={[
            styles.dialog,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <View style={styles.header}>
            <Text style={[styles.title, { color: semantic.text.primary }]} numberOfLines={1}>
              {line?.description || 'Editar producto'}
            </Text>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Cerrar edición de producto"
              hitSlop={8}
              onPress={onClose}
            >
              <Ionicons name="close-outline" size={22} color={semantic.text.secondary} />
            </Pressable>
          </View>

          <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false}>
            {discountPolicy && discountPolicy.source !== 'none' ? (
              <Text
                style={[
                  styles.infoChip,
                  { backgroundColor: semantic.bg.primary, color: semantic.text.secondary },
                ]}
              >
                {discountPolicy.label} {discountPolicy.percentage}% · ${discountPolicy.amount}
              </Text>
            ) : null}

            <View style={styles.grid}>
              <View style={styles.col}>
                <Controller
                  control={control}
                  name={`lines.${safeIndex}.code`}
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
                  name={`lines.${safeIndex}.description`}
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
                  name={`lines.${safeIndex}.quantity`}
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
                  name={`lines.${safeIndex}.unit_price`}
                  render={({ field: { onChange, onBlur, value } }) => (
                    <MoneyField
                      label="Precio unitario"
                      placeholder="0.00"
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
                  name={`lines.${safeIndex}.discount`}
                  render={({ field: { onChange, onBlur, value } }) => (
                    <DiscountInput
                      label="Descuento"
                      baseAmount={discountBase}
                      placeholder="0.00"
                      keyboardType="decimal-pad"
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
              <View style={styles.lineSummary}>
                {discountPolicy && discountPolicy.source !== 'none' ? (
                  <Text
                    style={[
                      styles.discountState,
                      {
                        color:
                          Math.abs(appliedDiscount - suggestedDiscount) < 0.01
                            ? semantic.status.success
                            : semantic.status.warning,
                      },
                    ]}
                  >
                    {Math.abs(appliedDiscount - suggestedDiscount) < 0.01
                      ? 'Descuento aplicado'
                      : 'Descuento editado manualmente'}
                  </Text>
                ) : null}
                <Text style={[styles.lineTotal, { color: semantic.text.primary }]}>
                  Total: ${totals.total.toFixed(2)}
                </Text>
              </View>
            </View>
          </ScrollView>

          <Button variant="primary" size="md" fullWidth onPress={onClose}>
            Listo
          </Button>
        </View>
      </View>
    </Modal>
  )
}

function toNumber(value: string | undefined): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const styles = StyleSheet.create({
  overlay: {
    alignItems: 'center',
    backgroundColor: overlay.surface.backdrop,
    flex: 1,
    justifyContent: 'center',
    padding: spacing[5],
  },
  dialog: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    maxHeight: '85%',
    maxWidth: 480,
    padding: spacing[5],
    width: '100%',
  },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  title: { flex: 1, fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  body: { gap: spacing[3] },
  infoChip: {
    alignSelf: 'flex-start',
    borderRadius: radius.full,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    overflow: 'hidden',
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
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
  lineSummary: { alignItems: 'flex-end', gap: spacing[1] - 2 },
  discountState: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  lineTotal: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
})
