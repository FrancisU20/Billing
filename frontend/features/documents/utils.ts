import { CONSUMIDOR_FINAL_ID_TYPE } from './constants'
import type { Document } from './types'

// SRI Res. NAC-DGERCGC25-00000014/00000017: anulacion "en linea" solo hasta el dia 7 del
// mes siguiente a la emision. No se ajusta al siguiente dia habil si cae feriado/fin de
// semana (mismo criterio que el backend, ver use_cases/annul_document.py).
const ANNULMENT_DEADLINE_DAY = 7

export function isWithinAnnulmentWindow(issuedAt: string): boolean {
  const [year, month, day] = issuedAt.split('-').map(Number)
  if (!year || !month || !day) return false

  const deadline = new Date(year, month, ANNULMENT_DEADLINE_DAY) // month is 0-indexed -> next month
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  deadline.setHours(0, 0, 0, 0)

  return today <= deadline
}

/**
 * Motivo de negocio (Res. NAC-DGERCGC25) por el que un documento no se puede anular, o
 * `null` si es elegible. No evalua permisos de rol (`canWrite`) — eso lo decide la
 * pantalla para ocultar la accion por completo en vez de explicarla.
 */
export function getAnnulBlockReason(document: Document): string | null {
  if (document.status !== 'AUTHORIZED') {
    return 'Solo se pueden anular documentos autorizados por el SRI.'
  }
  if (document.buyer_id_type === CONSUMIDOR_FINAL_ID_TYPE) {
    return 'Las facturas a Consumidor Final no se pueden anular (Res. NAC-DGERCGC25, vigente desde enero 2026).'
  }
  if (!isWithinAnnulmentWindow(document.issued_at)) {
    return 'El plazo legal para anular venció (hasta el día 7 del mes siguiente a la emisión).'
  }
  return null
}
