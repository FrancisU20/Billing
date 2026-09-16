import React, { useEffect, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { FormField } from '@/components/ui/FormField'
import { FormSection } from '@/components/ui/FormSection'
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
import { radius, spacing, typography } from '@/constants/tokens'
import { documentsApi } from '../api'
import { BuyerSection } from '../components/BuyerSection'
import { DocumentLineEditModal } from '../components/DocumentLineEditModal'
import { DocumentLineRow } from '../components/DocumentLineRow'
import { LockedInfoRow } from '../components/LockedInfoRow'
import { TotalsSummary } from '../components/TotalsSummary'
import { PAYMENT_METHOD_OPTIONS } from '../constants'
import {
  computeLineTotals,
  defaultEmitDocumentFormValues,
  ecuadorIssuedAtDisplay,
  formValuesToEmitDocumentInput,
} from '../form'
import { useDocumentLines } from '../hooks/useDocumentLines'
import { emitDocumentFormValuesSchema, type EmitDocumentFormValues } from '../schemas'

export function EmitDocumentScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [productPickerOpen, setProductPickerOpen] = useState(false)
  const [editingLineIndex, setEditingLineIndex] = useState<number | null>(null)
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
  const establishmentCode = useWatch({ control, name: 'establishment_code' })
  const emissionPointCode = useWatch({ control, name: 'emission_point_code' })
  const issuedAt = useWatch({ control, name: 'issued_at' })
  const paymentMethod = useWatch({ control, name: 'payment_method' })
  const overrideDiscountCeiling = useWatch({ control, name: 'override_discount_ceiling' })

  const campaignInput = campaign
    ? { active: campaign.active, percentage: campaign.percentage }
    : null
  const { fields, lines, productDiscountByLine, discountPreview, addProductLine, removeLine } =
    useDocumentLines(control, getValues, setValue, campaignInput)

  useEffect(() => {
    if (establishments.length === 0 || establishmentCode) return
    const first = establishments[0]
    setValue('establishment_code', first.code)
    if (first.emission_points.length > 0) {
      setValue('emission_point_code', first.emission_points[0].code)
    }
  }, [establishments, establishmentCode, setValue])

  const selectedEstablishment = establishments.find((est) => est.code === establishmentCode)

  const { submitting, error, submit } = useFormSubmit(async (values: EmitDocumentFormValues) => {
    const document = await documentsApi.emit(
      formValuesToEmitDocumentInput(values),
      createIdempotencyKey('document_emit'),
    )
    toast.success('Documento emitido — esperando autorización del SRI')
    router.replace(Routes.tenant.documentDetail(document.document_id) as Href)
  })

  const totals = computeLineTotals(lines ?? [])

  function handleProductSelected(product: Product) {
    addProductLine(product)
    setProductPickerOpen(false)
  }

  function handleRemoveLine(index: number) {
    removeLine(index)
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
            <FormSection
              title="Establecimiento y punto de emisión"
              icon="storefront-outline"
              fill
              contentStyle={styles.sectionBody}
            >
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
            <FormSection
              title="Fecha de emisión"
              icon="calendar-outline"
              fill
              contentStyle={styles.sectionBody}
            >
              <LockedInfoRow
                icon="calendar-outline"
                label="Fecha y hora Ecuador"
                value={issuedAtDisplay}
                meta={`Fecha SRI: ${issuedAt}`}
                monoMeta
              />
              {errors.issued_at?.message ? (
                <Text style={[styles.fieldError, { color: semantic.status.error }]}>
                  {errors.issued_at.message}
                </Text>
              ) : null}
            </FormSection>
          </View>
        </View>

        <FormSection title="Comprador" icon="person-outline" contentStyle={styles.sectionBody}>
          <BuyerSection control={control} setValue={setValue} errors={errors} />
        </FormSection>

        <View style={styles.twoColRow}>
          <View style={styles.halfColumn}>
            <FormSection
              title="Forma de pago"
              icon="card-outline"
              contentStyle={styles.sectionBody}
            >
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
            <FormSection
              title="Avanzado"
              icon="construct-outline"
              contentStyle={styles.sectionBody}
            >
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

        <FormSection title="Productos" icon="cube-outline" contentStyle={styles.sectionBody}>
          <DiscountContextBanner
            campaign={campaignInput}
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
                  onRemove={() => handleRemoveLine(index)}
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
        onSelect={handleProductSelected}
        campaign={campaignInput}
      />
      <DocumentLineEditModal
        index={editingLineIndex}
        control={control}
        errors={errors}
        onClose={() => setEditingLineIndex(null)}
        productDiscountPercentage={
          editingLineIndex !== null ? (productDiscountByLine[editingLineIndex] ?? null) : null
        }
        campaign={campaignInput}
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

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
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
  fieldError: { fontSize: typography.size.xs },
})
