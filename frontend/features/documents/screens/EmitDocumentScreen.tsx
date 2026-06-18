import React, { useEffect, useState } from 'react'
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
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { useEstablishments } from '@/features/sequences/hooks/useEstablishments'
import { ProductPickerModal } from '@/features/products/components/ProductPickerModal'
import type { Product } from '@/features/products/types'
import { Routes } from '@/constants/routes'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { documentsApi } from '../api'
import { BuyerSection } from '../components/BuyerSection'
import { DocumentLineItem } from '../components/DocumentLineItem'
import { PAYMENT_METHOD_OPTIONS } from '../constants'
import {
  computeLineTotals,
  defaultEmitDocumentFormValues,
  defaultEmitDocumentLine,
  formValuesToEmitDocumentInput,
} from '../form'
import { emitDocumentFormValuesSchema, type EmitDocumentFormValues } from '../schemas'

export function EmitDocumentScreen() {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()
  const [pickerLineIndex, setPickerLineIndex] = useState<number | null>(null)
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null
  const {
    establishments,
    loading: loadingEstablishments,
    error: establishmentsError,
    refresh: refreshEstablishments,
  } = useEstablishments(tenantId)

  const {
    control,
    handleSubmit,
    setValue,
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
  const paymentMethod = useWatch({ control, name: 'payment_method' })
  const lines = useWatch({ control, name: 'lines' })

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

  function applyProductToLine(product: Product) {
    if (pickerLineIndex === null) return
    setValue(`lines.${pickerLineIndex}.product_id`, product.id, { shouldDirty: true })
    setValue(`lines.${pickerLineIndex}.code`, product.sku, {
      shouldDirty: true,
      shouldValidate: true,
    })
    setValue(`lines.${pickerLineIndex}.description`, product.description || product.name, {
      shouldDirty: true,
      shouldValidate: true,
    })
    setValue(`lines.${pickerLineIndex}.unit_price`, product.unit_price, {
      shouldDirty: true,
      shouldValidate: true,
    })
    setValue(`lines.${pickerLineIndex}.iva_rate`, product.iva_rate, {
      shouldDirty: true,
      shouldValidate: true,
    })
    setPickerLineIndex(null)
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
        <FormSection title="Establecimiento y punto de emisión" icon="storefront-outline">
          <View style={styles.pillGrid}>
            {establishments.map((est) => (
              <Pill
                key={est.code}
                label={est.label}
                selected={establishmentCode === est.code}
                onPress={() => {
                  setValue('establishment_code', est.code, { shouldValidate: true })
                  setValue('emission_point_code', est.emission_points[0]?.code ?? '', {
                    shouldValidate: true,
                  })
                }}
              />
            ))}
          </View>
          {selectedEstablishment ? (
            <View style={styles.pillGrid}>
              {selectedEstablishment.emission_points.map((point) => (
                <Pill
                  key={point.code}
                  label={point.label}
                  selected={emissionPointCode === point.code}
                  onPress={() =>
                    setValue('emission_point_code', point.code, { shouldValidate: true })
                  }
                />
              ))}
            </View>
          ) : null}
        </FormSection>

        <FormSection title="Fecha de emisión" icon="calendar-outline">
          <Controller
            control={control}
            name="issued_at"
            render={({ field: { onChange, onBlur, value } }) => (
              <FormField
                label="Fecha"
                placeholder="2026-06-18"
                leftIcon="calendar-outline"
                error={errors.issued_at?.message}
                onChangeText={onChange}
                onBlur={onBlur}
                value={value}
                required
              />
            )}
          />
        </FormSection>

        <FormSection title="Comprador" icon="person-outline">
          <BuyerSection control={control} setValue={setValue} errors={errors} />
        </FormSection>

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

        <FormSection title="Líneas de detalle" icon="list-outline">
          {fields.map((field, index) => (
            <DocumentLineItem
              key={field.id}
              index={index}
              control={control}
              errors={errors}
              canRemove={fields.length > 1}
              onPickProduct={() => setPickerLineIndex(index)}
              onRemove={() => remove(index)}
              onChangeIvaRate={(rate) =>
                setValue(`lines.${index}.iva_rate`, rate, {
                  shouldDirty: true,
                  shouldValidate: true,
                })
              }
            />
          ))}
          <Button variant="outline" size="md" onPress={() => append(defaultEmitDocumentLine())}>
            Agregar línea
          </Button>
        </FormSection>

        <View
          style={[
            styles.totalsCard,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <TotalRow label="Subtotal" value={totals.subtotal} />
          <TotalRow label="Descuento" value={totals.totalDiscount} />
          <TotalRow label="IVA 15%" value={totals.iva15} />
          <TotalRow label="IVA 5%" value={totals.iva5} />
          <TotalRow label="Total" value={totals.total} emphasis />
        </View>

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
        visible={pickerLineIndex !== null}
        onClose={() => setPickerLineIndex(null)}
        onSelect={applyProductToLine}
      />
    </View>
  )
}

function FormSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: keyof typeof Ionicons.glyphMap
  children: React.ReactNode
}) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.section,
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

function TotalRow({
  label,
  value,
  emphasis = false,
}: {
  label: string
  value: number
  emphasis?: boolean
}) {
  const { semantic } = useTheme()
  return (
    <View style={styles.totalRow}>
      <Text
        style={[
          styles.totalLabel,
          emphasis && styles.totalLabelEmphasis,
          { color: emphasis ? semantic.text.primary : semantic.text.secondary },
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
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  section: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[4] },
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
  totalsCard: { borderRadius: radius.md, borderWidth: 1, gap: spacing[2], padding: spacing[4] },
  totalRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  totalLabel: { fontSize: typography.size.sm },
  totalLabelEmphasis: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  totalValue: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  totalValueEmphasis: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
})
