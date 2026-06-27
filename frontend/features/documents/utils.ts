import { formatDateTime } from '@/lib/utils/format'
import type { Document } from './types'

/**
 * Motivo de negocio por el que un documento no se puede acreditar con una Nota de
 * Crédito, o `null` si es elegible. A diferencia de la vieja anulación local
 * (deprecada), Nota de Crédito SÍ llega al SRI y NO tiene excepción de Consumidor
 * Final ni ventana de plazo — esa restricción era específica del trámite manual de
 * anulación en línea (Res. NAC-DGERCGC25), no de las Notas de Crédito. No evalúa
 * permisos de rol (`canWrite`) — eso lo decide la pantalla para ocultar la acción por
 * completo en vez de explicarla.
 */
export function getCreditNoteBlockReason(document: Document): string | null {
  if (document.doc_type !== '01') {
    return 'Una nota de crédito solo puede acreditar una factura, no otra nota de crédito.'
  }
  if (document.status !== 'AUTHORIZED') {
    return 'Solo se puede emitir una nota de crédito sobre documentos autorizados por el SRI.'
  }
  if (document.annulled_by_credit_note_id) {
    return 'Esta factura ya está siendo anulada o ya fue anulada mediante una nota de crédito.'
  }
  return null
}

/**
 * Texto del banner "anulada" en el detalle de una factura (doc_type='01') con
 * `annulled_by_credit_note_id` seteado. El `status` de la factura nunca cambia (sigue
 * AUTHORIZED ante el SRI) — este texto refleja el estado real en vivo de la Nota de
 * Crédito que la anula, no un estado falso de la factura. `creditNote` es `null`/
 * `undefined` mientras el detalle de la NC todavía está cargando (ver `useDocument`).
 */
export function getAnnulmentBannerText(creditNote: Document | null | undefined): string {
  if (!creditNote) {
    return 'Esta factura está siendo anulada mediante una nota de crédito.'
  }
  const seq = creditNote.sequential_display
  switch (creditNote.status) {
    case 'AUTHORIZED':
      return `Esta factura fue anulada mediante la Nota de Crédito ${seq}${
        creditNote.authorized_at ? ` el ${formatDateTime(creditNote.authorized_at)}` : ''
      }.`
    case 'REJECTED':
      return (
        `El intento de anulación mediante la Nota de Crédito ${seq} fue rechazado por el ` +
        'SRI — puedes reintentarlo desde el módulo de Notas de Crédito.'
      )
    case 'FAILED_PERMANENT':
      return (
        `No pudimos confirmar la anulación mediante la Nota de Crédito ${seq} con el SRI ` +
        'tras varios intentos. Contacta soporte.'
      )
    default:
      return (
        `Esta factura está siendo anulada mediante la Nota de Crédito ${seq} — esperando ` +
        'autorización del SRI.'
      )
  }
}
