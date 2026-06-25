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
  return null
}
