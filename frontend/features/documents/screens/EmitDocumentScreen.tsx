import React, { useEffect, useRef, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Controller, useFieldArray, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { FormField } from '@/components/ui/FormField'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useRefreshOnFocus } from '@/lib/hooks/useRefreshOnFocus'
import { useTheme } from '@/lib/theme-context'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { useEstablishments } from '@/features/sequences/hooks/useEstablishments'
import { ProductPickerModal } from '@/features/products/components/ProductPickerModal'
import { useDiscountCampaign } from '@/features/products/hooks/useDiscountCampaign'
import type { Product } from '@/features/products/types'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { documentsApi } from '../api'
import { BuyerSection } from '../components/BuyerSection'
import { DocumentLineEditModal } from '../components/DocumentLineEditModal'
import { DocumentLineRow } from '../components/DocumentLineRow'
import { TotalsSummary } from '../components/TotalsSummary'
import { PAYMENT_METHOD_OPTIONS } from '../constants'
import {
  computeLineTotals,
  defaultEmitDocumentFormValues,
  ecuadorIssuedAtDisplay,
  formValuesToEmitDocumentInput,
  resolveDiscountPolicy,
  resolveSuggestedDiscount,
  shouldAutoApplySuggestedDiscount,
} from '../form'
import { emitDocumentFormValuesSchema, type EmitDocumentFormValues } from '../schemas'

export function EmitDocumentScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [productPickerOpen, setProductPickerOpen] = useState(false)
  const [editingLineIndex, setEditingLineIndex] = useState<number | null>(null)
  const [productDiscountByLine, setProductDiscountByLine] = useState<Record<number, string | null>>(
    {},
  )
  const lastSuggestedDiscountByLine = useRef<Record<number, string>>({})
  const [issuedAtDisplay] = useState(() => ecuadorIssuedAtDisplay())
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const {
    establishments,
    loading: loadingEstablishments,
    error: establishmentsError,
    refresh: refreshEstablishments,
  } = useEstablishments(tenantId)
  const { campaign, refresh: refreshCampaign } = useDiscountCampaign()

  useRefreshOnFocus(refreshEstablishments)
  useRefreshOnFocus(refreshCampaign)

  const {
    control,
    handleSubmit,
    setValue,
    getValues,
    formState: { errors, isValid },
  } = useForm<EmitDocumentFormValues>({
    resolver: zodResolver(emitDocumentFormValuesSchema),
    defaultValues: defaultEmitDocumentFormValues('', ''),
    mode: 'onChange',
    reValidateMode: 'onChange',
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'lines' })
  const establishmentCode = useWatch({ control, name: 'establishment_code' })
  const emissionPointCode = useWatch({ control, name: 'emission_point_code' })
  const issuedAt = useWatch({ control, name: 'issued_at' })
  const paymentMethod = useWatch({ control, name: 'payment_method' })
  const lines = useWatch({ control, name: 'lines' })
  const overrideDiscountCeiling = useWatch({ control, name: 'override_discount_ceiling' })

  useEffect(() => {
    if (establishments.length === 0 || establishmentCode) return
    const first = establishments[0]
    setValue('establishment_code', first.code)
    if (first.emission_points.length > 0) {
      setValue('emission_point_code', first.emission_points[0].code)
    }
  }, [establishments, establishmentCode, setValue])

  const selectedEstablishment = establishments.find((est) => est.code === establishmentCode)

  useEffect(() => {
    for (const [index, line] of (lines ?? []).entries()) {
      const suggestedDiscount = resolveSuggestedDiscount(
        line.quantity,
        line.unit_price,
        productDiscountByLine[index] ?? null,
        campaign ? { active: campaign.active, percentage: campaign.percentage } : null,
      )

      if (
        shouldAutoApplySuggestedDiscount(
          line.discount,
          lastSuggestedDiscountByLine.current[index],
          suggestedDiscount,
        )
      ) {
        setValue(`lines.${index}.discount`, suggestedDiscount, {
          shouldDirty: true,
          shouldValidate: true,
        })
      }

      lastSuggestedDiscountByLine.current[index] = suggestedDiscount
    }
  }, [campaign, lines, productDiscountByLine, setValue])

  const { submitting, error, submit } = useFormSubmit(async (values: EmitDocumentFormValues) => {
    const document = await documentsApi.emit(
      formValuesToEmitDocumentInput(values),
      createIdempotencyKey('document_emit'),
    )
    toast.success('Documento emitido — esperando autorización del SRI')
    router.replace(Routes.tenant.documentDetail(document.document_id) as Href)
  })

  const totals = computeLineTotals(lines ?? [])
  const discountPreview = computeDiscountPreview(
    lines ?? [],
    productDiscountByLine,
    campaign ? { active: campaign.active, percentage: campaign.percentage } : null,
  )

  function incrementLineQuantity(index: number) {
    const current = Number(getValues(`lines.${index}.quantity`)) || 0
    setValue(`lines.${index}.quantity`, String(current + 1), {
      shouldDirty: true,
      shouldValidate: true,
    })
  }

  function addProductLine(product: Product) {
    const existingIndex = (lines ?? []).findIndex((line) => line.product_id === product.id)
    if (existingIndex >= 0) {
      incrementLineQuantity(existingIndex)
      setProductPickerOpen(false)
      return
    }

    const newIndex = fields.length
    const suggestedDiscount = resolveSuggestedDiscount(
      '1',
      product.unit_price,
      product.discount_percentage,
      campaign ? { active: campaign.active, percentage: campaign.percentage } : null,
    )
    append({
      product_id: product.id,
      code: product.invoice_code,
      description: product.description || product.name,
      quantity: '1',
      unit_price: product.unit_price,
      discount: suggestedDiscount,
      iva_rate: product.iva_rate,
    })
    setProductDiscountByLine((current) => ({ ...current, [newIndex]: product.discount_percentage }))
    lastSuggestedDiscountByLine.current[newIndex] = suggestedDiscount
    setProductPickerOpen(false)
  }

  function removeLine(index: number) {
    remove(index)
    setProductDiscountByLine((current) => reindexByRemovedLine(current, index))
    lastSuggestedDiscountByLine.current = reindexByRemovedLine(
      lastSuggestedDiscountByLine.current,
      index,
    )
    setEditingLineIndex((current) => (current === index ? null : current))
  }

  if (loadingEstablishments) {
    return <LoadingSpinner fullScreen label="Cargando establecimientos..." />
  }

  if (establishmentsError) {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <AppNavBar title="Emitir documento" canGoBack />
        <EmptyState
          icon="alert-circle-outline"
          title="No se pudieron cargar los establecimientos"
          description={establishmentsError.message}
          action={{ label: 'Reintentar', onPress: refreshEstablishments }}
        />
      </View>
    )
  }

  if (establishments.length === 0) {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <AppNavBar title="Emitir documento" canGoBack />
        <EmptyState
          icon="storefront-outline"
          title="Sin establecimientos"
          description="Sube tu certificado digital para habilitar la emisión — al cargarlo se crea automáticamente tu punto de pruebas."
          action={{
            label: 'Ir al dashboard',
            onPress: () => router.push(Routes.tenant.dashboard as Href),
          }}
        />
      </View>
    )
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Emitir documento" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.twoColRow}>
          <View style={styles.halfColumn}>
            <FormSection title="Establecimiento y punto de emisión" icon="storefront-outline" fill>
              {establishments.length > 1 ? (
                <View style={styles.subField}>
                  <Text style={[styles.subFieldLabel, { color: semantic.text.secondary }]}>
                    Establecimiento
                  </Text>
                  <SegmentedControl
                    stretch
                    value={establishmentCode}
                    options={establishments.map((est) => ({ value: est.code, label: est.label }))}
                    onChange={(code) => {
                      setValue('establishment_code', code, { shouldValidate: true })
                      const est = establishments.find((candidate) => candidate.code === code)
                      setValue('emission_point_code', est?.emission_points[0]?.code ?? '', {
                        shouldValidate: true,
                      })
                    }}
                  />
                </View>
              ) : (
                <LockedInfoRow
                  icon="storefront-outline"
                  label="Establecimiento"
                  value={selectedEstablishment?.label ?? ''}
                />
              )}
              {selectedEstablishment && selectedEstablishment.emission_points.length > 1 ? (
                <View style={styles.subField}>
                  <Text style={[styles.subFieldLabel, { color: semantic.text.secondary }]}>
                    Punto de emisión
                  </Text>
                  <SegmentedControl
                    stretch
                    value={emissionPointCode}
                    options={selectedEstablishment.emission_points.map((point) => ({
                      value: point.code,
                      label: point.label,
                    }))}
                    onChange={(code) =>
                      setValue('emission_point_code', code, { shouldValidate: true })
                    }
                  />
                </View>
              ) : selectedEstablishment ? (
                <LockedInfoRow
                  icon="pricetags-outline"
                  label="Punto de emisión"
                  value={
                    selectedEstablishment.emission_points.find(
                      (point) => point.code === emissionPointCode,
                    )?.label ?? ''
                  }
                />
              ) : null}
            </FormSection>
          </View>

          <View style={styles.halfColumn}>
            <FormSection title="Fecha de emisión" icon="calendar-outline" fill>
              <LockedIssuedAt value={issuedAtDisplay} sriDate={issuedAt} />
              {errors.issued_at?.message ? (
                <Text style={[styles.fieldError, { color: semantic.status.error }]}>
                  {errors.issued_at.message}
                </Text>
              ) : null}
            </FormSection>
          </View>
        </View>

        <FormSection title="Comprador" icon="person-outline">
          <BuyerSection control={control} setValue={setValue} errors={errors} />
        </FormSection>

        <View style={styles.twoColRow}>
          <View style={styles.halfColumn}>
            <FormSection title="Forma de pago" icon="card-outline">
              <View style={styles.pillGrid}>
                {PAYMENT_METHOD_OPTIONS.map((option) => (
                  <Pill
                    key={option.value}
                    label={option.label}
                    selected={paymentMethod === option.value}
                    onPress={() =>
                      setValue('payment_method', option.value, {
                        shouldDirty: true,
                        shouldValidate: true,
                      })
                    }
                  />
                ))}
              </View>
            </FormSection>
          </View>

          <View style={styles.halfColumn}>
            <FormSection title="Avanzado" icon="construct-outline">
              <SegmentedControl
                value={overrideDiscountCeiling ? 'yes' : 'no'}
                options={[
                  { label: 'Techo de descuento normal', value: 'no' },
                  { label: 'Anular techo de descuento', value: 'yes' },
                ]}
                onChange={(next) =>
                  setValue('override_discount_ceiling', next === 'yes', { shouldValidate: true })
                }
              />
              {overrideDiscountCeiling ? (
                <Controller
                  control={control}
                  name="override_reason"
                  render={({ field: { onChange, onBlur, value } }) => (
                    <FormField
                      label="Motivo del descuento excepcional"
                      placeholder="Ej. gesto comercial autorizado por el gerente"
                      leftIcon="alert-circle-outline"
                      error={errors.override_reason?.message}
                      onChangeText={onChange}
                      onBlur={onBlur}
                      value={value}
                      required
                    />
                  )}
                />
              ) : (
                <Text style={[styles.note, { color: semantic.text.tertiary }]}>
                  Por defecto, ningún descuento puede superar el máximo del catálogo o la campaña
                  activa. Esta opción queda registrada con tu usuario y motivo.
                </Text>
              )}
            </FormSection>
          </View>
        </View>

        <FormSection title="Productos" icon="cube-outline">
          <DiscountContextBanner
            campaign={
              campaign ? { active: campaign.active, percentage: campaign.percentage } : null
            }
            discountedLines={discountPreview.discountedLines}
            suggestedDiscount={discountPreview.suggestedDiscount}
          />

          {fields.length === 0 ? (
            <Text
              style={[
                styles.note,
                { color: errors.lines?.message ? semantic.status.error : semantic.text.tertiary },
              ]}
            >
              {errors.lines?.message ?? 'Sin productos todavía. Usa "Agregar producto".'}
            </Text>
          ) : (
            <View style={styles.linesList}>
              {fields.map((field, index) => (
                <DocumentLineRow
                  key={field.id}
                  index={index}
                  control={control}
                  onPress={() => setEditingLineIndex(index)}
                  onRemove={() => removeLine(index)}
                />
              ))}
            </View>
          )}

          <Button variant="outline" size="md" onPress={() => setProductPickerOpen(true)}>
            Agregar producto
          </Button>
        </FormSection>

        <TotalsSummary
          subtotal={totals.subtotal}
          totalDiscount={totals.totalDiscount}
          suggestedDiscount={discountPreview.suggestedDiscount}
          iva15={totals.iva15}
          iva5={totals.iva5}
          total={totals.total}
        />

        {error ? <ApiErrorBanner error={error} /> : null}

        <Button
          variant="primary"
          size="lg"
          fullWidth
          isLoading={submitting}
          isDisabled={!isValid}
          onPress={handleSubmit(submit)}
        >
          Emitir documento
        </Button>
      </ScrollView>
      <ProductPickerModal
        visible={productPickerOpen}
        onClose={() => setProductPickerOpen(false)}
        onSelect={addProductLine}
        campaign={campaign ? { active: campaign.active, percentage: campaign.percentage } : null}
      />
      <DocumentLineEditModal
        index={editingLineIndex}
        control={control}
        errors={errors}
        onClose={() => setEditingLineIndex(null)}
        productDiscountPercentage={
          editingLineIndex !== null ? (productDiscountByLine[editingLineIndex] ?? null) : null
        }
        campaign={campaign ? { active: campaign.active, percentage: campaign.percentage } : null}
        onChangeIvaRate={(rate) => {
          if (editingLineIndex === null) return
          setValue(`lines.${editingLineIndex}.iva_rate`, rate, {
            shouldDirty: true,
            shouldValidate: true,
          })
        }}
      />
    </View>
  )
}

function DiscountContextBanner({
  campaign,
  discountedLines,
  suggestedDiscount,
}: {
  campaign: { active: boolean; percentage: string } | null
  discountedLines: number
  suggestedDiscount: number
}) {
  const { semantic } = useTheme()
  const campaignActive = campaign?.active && Number(campaign.percentage) > 0

  if (!campaignActive && discountedLines === 0) {
    return null
  }

  return (
    <View
      style={[
        styles.discountBanner,
        { backgroundColor: semantic.accent.subtle, borderColor: semantic.accent.muted },
      ]}
    >
      <Ionicons name="pricetag-outline" size={18} color={semantic.accent.default} />
      <View style={styles.discountBannerText}>
        <Text style={[styles.discountBannerTitle, { color: semantic.text.primary }]}>
          Descuentos visibles antes de emitir
        </Text>
        <Text style={[styles.discountBannerBody, { color: semantic.text.secondary }]}>
          {campaignActive ? `Campaña global activa: ${Number(campaign.percentage)}%. ` : ''}
          {discountedLines > 0
            ? `${discountedLines} línea${discountedLines === 1 ? '' : 's'} con descuento sugerido por $${suggestedDiscount.toFixed(2)}.`
            : 'Selecciona productos con descuento o aplica descuento manual por línea.'}
        </Text>
      </View>
    </View>
  )
}

function LockedIssuedAt({ value, sriDate }: { value: string; sriDate: string }) {
  return (
    <LockedInfoRow
      icon="calendar-outline"
      label="Fecha y hora Ecuador"
      value={value}
      meta={`Fecha SRI: ${sriDate}`}
    />
  )
}

/** Caja "no editable" generica — mismo lenguaje visual para todo dato fijo que no es un
 * Input deshabilitado (`Input.tsx` ya cubre ese caso) sino un valor sin alternativa real
 * para elegir, ej. el unico establecimiento/punto de emision del tenant. Evita que un
 * `SegmentedControl` con una sola opcion se vea como un boton vacio sin proposito. */
function LockedInfoRow({
  icon,
  label,
  value,
  meta,
}: {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  value: string
  meta?: string
}) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.lockedDate,
        { backgroundColor: semantic.bg.primary, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.lockedDateIcon}>
        <Ionicons name={icon} size={18} color={semantic.accent.default} />
      </View>
      <View style={styles.lockedDateText}>
        <Text style={[styles.lockedDateLabel, { color: semantic.text.secondary }]}>{label}</Text>
        <Text style={[styles.lockedDateValue, { color: semantic.text.primary }]}>{value}</Text>
        {meta ? (
          <Text style={[styles.lockedDateMeta, { color: semantic.text.tertiary }]}>{meta}</Text>
        ) : null}
      </View>
      <Ionicons name="lock-closed-outline" size={18} color={semantic.text.tertiary} />
    </View>
  )
}

function FormSection({
  title,
  icon,
  children,
  fill = false,
}: {
  title: string
  icon: keyof typeof Ionicons.glyphMap
  children: React.ReactNode
  /** Solo para parejas dentro de `twoColRow`, donde el sibling con mas contenido debe
   * marcar la altura de la fila — `halfColumn` ya queda con esa altura via el
   * `alignItems: 'stretch'` por defecto de `twoColRow`, y `fill` hace que este card
   * la ocupe en vez de quedarse en su alto de contenido. No usar en cards standalone
   * (Comprador, Productos, etc.): ahi el padre no tiene una altura real que repartir y
   * `flex: 1` colapsa el card a 0 con el contenido desbordando por debajo. */
  fill?: boolean
}) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.section,
        fill && styles.sectionFill,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.sectionHeader}>
        <View style={[styles.sectionIcon, { backgroundColor: semantic.accent.subtle }]}>
          <Ionicons name={icon} size={17} color={semantic.accent.default} />
        </View>
        <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>{title}</Text>
      </View>
      <View style={styles.sectionBody}>{children}</View>
    </View>
  )
}

function Pill({
  label,
  selected,
  onPress,
}: {
  label: string
  selected: boolean
  onPress: () => void
}) {
  const { semantic } = useTheme()
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.pill,
        {
          backgroundColor: selected
            ? semantic.accent.subtle
            : pressed
              ? semantic.bg.secondary
              : semantic.bg.primary,
          borderColor: selected ? semantic.accent.default : semantic.border.default,
        },
      ]}
    >
      <Text
        style={[
          styles.pillText,
          { color: selected ? semantic.accent.default : semantic.text.secondary },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  )
}

function computeDiscountPreview(
  lines: EmitDocumentFormValues['lines'],
  productDiscountByLine: Record<number, string | null>,
  campaign: { active: boolean; percentage: string } | null,
): { discountedLines: number; suggestedDiscount: number } {
  return lines.reduce(
    (acc, line, index) => {
      const policy = resolveDiscountPolicy(
        line.quantity,
        line.unit_price,
        productDiscountByLine[index] ?? null,
        campaign,
      )
      const amount = Number(policy.amount)
      if (policy.source !== 'none' && Number.isFinite(amount) && amount > 0) {
        acc.discountedLines += 1
        acc.suggestedDiscount += amount
      }
      return acc
    },
    { discountedLines: 0, suggestedDiscount: 0 },
  )
}

function reindexByRemovedLine<T>(
  values: Record<number, T>,
  removedIndex: number,
): Record<number, T> {
  return Object.entries(values).reduce<Record<number, T>>((next, [key, value]) => {
    const index = Number(key)
    if (index < removedIndex) {
      next[index] = value
    } else if (index > removedIndex) {
      next[index - 1] = value
    }
    return next
  }, {})
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  section: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[4],
  },
  sectionFill: { flex: 1 },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  sectionIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  sectionTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  sectionBody: { gap: spacing[3] },
  twoColRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  halfColumn: { flex: 1, minWidth: 280 },
  subField: { gap: spacing[2] },
  subFieldLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  linesList: { gap: spacing[2] },
  discountBanner: {
    alignItems: 'flex-start',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[2],
    padding: spacing[3],
  },
  discountBannerText: { flex: 1, gap: spacing[1] - 2 },
  discountBannerTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  discountBannerBody: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.5 },
  note: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.5 },
  pillGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  pill: {
    alignItems: 'center',
    borderRadius: radius.full,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: spacing[3],
  },
  pillText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  lockedDate: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    minHeight: 66,
    padding: spacing[3],
  },
  lockedDateIcon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  lockedDateText: { flex: 1, gap: spacing[1] - 2 },
  lockedDateLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  lockedDateValue: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  lockedDateMeta: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
  fieldError: { fontSize: typography.size.xs },
})
