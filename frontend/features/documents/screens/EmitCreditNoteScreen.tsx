import React, { useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import type { Href } from 'expo-router'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { AppNavBar } from '@/features/navigation/components/AppNavBar'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { FormField } from '@/components/ui/FormField'
import { FormSection } from '@/components/ui/FormSection'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { radius, spacing, typography } from '@/constants/tokens'
import { documentsApi } from '../api'
import { BuyerReadOnlySection } from '../components/BuyerReadOnlySection'
import { InvoicePickerModal } from '../components/InvoicePickerModal'
import { LockedInfoRow } from '../components/LockedInfoRow'
import { TotalsSummary } from '../components/TotalsSummary'
import {
  computeCreditNoteLinePreview,
  computeCreditNoteTotals,
  creditNoteFormValuesToInput,
  defaultCreditNoteFormValues,
} from '../creditNoteForm'
import { useDocument } from '../hooks/useDocument'
import { emitCreditNoteFormValuesSchema } from '../schemas'
import { getCreditNoteBlockReason } from '../utils'
import type { CreditNoteFormLine, Document, EmitCreditNoteFormValues } from '../types'

export function EmitCreditNoteScreen() {
  const router = useRouter()
  const { semantic } = useTheme()
  const params = useLocalSearchParams<{ parent?: string }>()
  const [pickedParent, setPickedParent] = useState<Document | null>(null)
  const [pickerOpen, setPickerOpen] = useState(!params.parent)

  const {
    document: fetchedParent,
    loading: loadingParent,
    error: parentError,
  } = useDocument(params.parent ?? null)
  const parent = params.parent ? fetchedParent : pickedParent

  if (params.parent && loadingParent) {
    return <LoadingSpinner fullScreen label="Cargando factura..." />
  }

  if (params.parent && parentError) {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <AppNavBar title="Nota de crédito" canGoBack />
        <EmptyState
          icon="alert-circle-outline"
          title="No se pudo cargar la factura"
          description={parentError.message}
          action={{ label: 'Volver', onPress: () => router.back() }}
        />
      </View>
    )
  }

  const blockReason = parent ? getCreditNoteBlockReason(parent) : null
  if (parent && blockReason) {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <AppNavBar title="Nota de crédito" canGoBack />
        <EmptyState
          icon="ban-outline"
          title="No se puede acreditar esta factura"
          description={blockReason}
          action={{ label: 'Volver', onPress: () => router.back() }}
        />
      </View>
    )
  }

  if (!parent) {
    return (
      <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
        <AppNavBar title="Nota de crédito" canGoBack />
        <EmptyState
          icon="document-text-outline"
          title="Elige una factura"
          description="Busca la factura autorizada que quieres acreditar parcialmente."
          action={{ label: 'Buscar factura', onPress: () => setPickerOpen(true) }}
        />
        <InvoicePickerModal
          visible={pickerOpen}
          onClose={() => {
            setPickerOpen(false)
            if (!pickedParent) router.back()
          }}
          onSelect={(document) => {
            setPickedParent(document)
            setPickerOpen(false)
          }}
        />
      </View>
    )
  }

  return <CreditNoteForm parent={parent} />
}

function CreditNoteForm({ parent }: { parent: Document }) {
  const router = useRouter()
  const toast = useToast()
  const { semantic } = useTheme()

  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors, isValid },
  } = useForm<EmitCreditNoteFormValues>({
    resolver: zodResolver(emitCreditNoteFormValuesSchema),
    defaultValues: defaultCreditNoteFormValues(parent, false),
    mode: 'onChange',
  })
  const lines = useWatch({ control, name: 'lines' })
  const creditNoteReason = useWatch({ control, name: 'credit_note_reason' })

  const { submitting, error, submit } = useFormSubmit(async (values: EmitCreditNoteFormValues) => {
    const document = await documentsApi.emitCreditNote(
      creditNoteFormValuesToInput(values, parent.document_id),
      createIdempotencyKey('document_emit_credit_note'),
    )
    toast.success('Nota de crédito emitida — esperando autorización del SRI')
    router.replace(Routes.tenant.documentDetail(document.document_id) as Href)
  })

  const totals = computeCreditNoteTotals(lines ?? [])

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="Nota de crédito" canGoBack />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <FormSection
          title="Factura acreditada"
          icon="document-text-outline"
          contentStyle={styles.sectionBody}
        >
          <LockedInfoRow
            icon="document-text-outline"
            label="Factura"
            value={parent.sequential_display}
            meta={`Total original: $${parent.total}`}
          />
        </FormSection>

        <FormSection title="Comprador" icon="person-outline" contentStyle={styles.sectionBody}>
          <BuyerReadOnlySection
            buyerIdType={parent.buyer_id_type}
            buyerId={parent.buyer_id}
            buyerName={parent.buyer_name}
            buyerEmail={parent.buyer_email}
          />
        </FormSection>

        <FormSection title="Motivo" icon="alert-circle-outline" contentStyle={styles.sectionBody}>
          <FormField
            label="Motivo de la nota de crédito"
            placeholder="Ej. devolución de mercadería"
            leftIcon="alert-circle-outline"
            error={errors.credit_note_reason?.message}
            onChangeText={(value) =>
              setValue('credit_note_reason', value, { shouldDirty: true, shouldValidate: true })
            }
            value={creditNoteReason}
            required
          />
        </FormSection>

        <FormSection
          title="Líneas a acreditar"
          icon="cube-outline"
          contentStyle={styles.sectionBody}
        >
          <Text style={[styles.note, { color: semantic.text.tertiary }]}>
            Puedes bajar la cantidad acreditada por línea — nunca agregar líneas nuevas ni superar
            la cantidad original.
          </Text>
          <View style={styles.linesList}>
            {(lines ?? []).map((line, index) => (
              <CreditNoteLineRow
                key={`${line.parent_line_index}-${line.code}`}
                line={line}
                error={errors.lines?.[index]?.quantity?.message}
                onChangeQuantity={(value) =>
                  setValue(`lines.${index}.quantity`, value, {
                    shouldDirty: true,
                    shouldValidate: true,
                  })
                }
              />
            ))}
          </View>
        </FormSection>

        <TotalsSummary
          subtotal={totals.subtotal}
          totalDiscount={0}
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
          Emitir nota de crédito
        </Button>
      </ScrollView>
    </View>
  )
}

function CreditNoteLineRow({
  line,
  error,
  onChangeQuantity,
}: {
  line: CreditNoteFormLine
  error?: string
  onChangeQuantity: (value: string) => void
}) {
  const { semantic } = useTheme()
  const preview = computeCreditNoteLinePreview(line)
  return (
    <View
      style={[
        styles.lineRow,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.lineInfo}>
        <Text style={[styles.lineName, { color: semantic.text.primary }]} numberOfLines={1}>
          {line.description}
        </Text>
        <Text style={[styles.lineMeta, { color: semantic.text.tertiary }]} numberOfLines={1}>
          {line.code} · ${line.unit_price} c/u · IVA{' '}
          {line.iva_rate === 'EXENTO' ? 'Exento' : `${line.iva_rate}%`}
        </Text>
      </View>
      <View style={styles.lineQuantity}>
        <FormField
          label={`Cantidad (de ${line.original_quantity})`}
          keyboardType="decimal-pad"
          value={line.quantity}
          onChangeText={onChangeQuantity}
          error={error}
        />
      </View>
      <View style={styles.lineTotal}>
        <Text style={[styles.lineTotalLabel, { color: semantic.text.tertiary }]}>Total</Text>
        <Text style={[styles.lineTotalValue, { color: semantic.accent.default }]}>
          ${preview.total.toFixed(2)}
        </Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { gap: spacing[4], padding: spacing[5], paddingBottom: spacing[12] },
  sectionBody: { gap: spacing[3] },
  note: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.5 },
  linesList: { gap: spacing[2] },
  lineRow: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    padding: spacing[3],
  },
  lineInfo: { flex: 1, gap: spacing[1] - 2, minWidth: 160 },
  lineName: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  lineMeta: { fontSize: typography.size.xs },
  lineQuantity: { minWidth: 140 },
  lineTotal: { alignItems: 'flex-end', gap: spacing[1] },
  lineTotalLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  lineTotalValue: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
})
