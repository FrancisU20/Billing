import { useToast } from '@/components/feedback/Toast'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { documentsApi } from '../api'

/**
 * Reintenta un documento REJECTED (Factura o NC) reusando la misma clave de
 * acceso/secuencial — ver RetryDocumentUseCase en backend. Compartido por
 * DocumentsListScreen y CreditNoteInvoicesListScreen (mismo `DocumentListItem` en
 * ambos), por eso vive como hook en vez de duplicarse en cada pantalla.
 */
export function useRetryDocument(onRetried: () => void) {
  const toast = useToast()
  return useFormSubmit(async (documentId: string) => {
    await documentsApi.retry(documentId, createIdempotencyKey('document_retry'))
    toast.success('Documento reenviado al SRI — esperando autorización')
    onRetried()
  })
}
