import React, { useState } from 'react'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { FormField } from '@/components/ui/FormField'
import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { Routes } from '@/constants/routes'
import { documentsApi } from '../api'
import { creditNoteFormValuesToInput, defaultCreditNoteFormValues } from '../creditNoteForm'
import type { Document } from '../types'

interface AnnulInvoiceModalProps {
  visible: boolean
  document: Document | null
  onClose: () => void
}

/**
 * "Anular factura" = Nota de Credito (04) al 100% de cada linea de `document`. El
 * usuario solo ingresa el motivo; las lineas se calculan en background con
 * defaultCreditNoteFormValues(document, locked=true) — mismo calculo que usa la
 * pantalla de Nota de Credito parcial — sin mostrarlas en UI.
 */
export function AnnulInvoiceModal({ visible, document, onClose }: AnnulInvoiceModalProps) {
  const router = useRouter()
  const toast = useToast()
  const [reason, setReason] = useState('')

  const { submitting, error, submit } = useFormSubmit(async () => {
    if (!document) return
    const values = defaultCreditNoteFormValues(document, true)
    const input = creditNoteFormValuesToInput(
      { ...values, credit_note_reason: reason },
      document.document_id,
    )
    const creditNote = await documentsApi.emitCreditNote(
      input,
      createIdempotencyKey('document_emit_credit_note'),
    )
    toast.success('Factura anulada — esperando autorización del SRI')
    setReason('')
    onClose()
    router.replace(Routes.tenant.documentDetail(creditNote.document_id) as Href)
  })

  if (!document) return null

  return (
    <ConfirmDialog
      visible={visible}
      title="Anular factura"
      message={`Se emitirá una nota de crédito por el 100% de la factura ${document.sequential_display} ($${document.total}).`}
      confirmLabel="Anular factura"
      variant="danger"
      icon="ban-outline"
      isLoading={submitting}
      confirmDisabled={reason.trim().length === 0}
      onCancel={() => {
        setReason('')
        onClose()
      }}
      onConfirm={submit}
    >
      <FormField
        label="Motivo de la anulación"
        placeholder="Ej. error en datos del comprador"
        leftIcon="alert-circle-outline"
        value={reason}
        onChangeText={setReason}
        maxLength={300}
        required
      />
      {error ? <ApiErrorBanner error={error} /> : null}
    </ConfirmDialog>
  )
}
