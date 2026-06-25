import type { BadgeVariant } from '@/components/ui/Badge'
import type { BuyerIdType, BuyerMode, DocumentStatus, IvaRate, PaymentMethod } from './types'

export const DOCUMENTS_PAGE_SIZE = 30

// SRI XSD caps codigoPrincipal/codigoAuxiliar at 25 chars (Ficha Tecnica SRI Anexo 1).
export const LINE_CODE_MAX_LENGTH = 25

export const CONSUMIDOR_FINAL_ID_TYPE: BuyerIdType = '07'
export const CONSUMIDOR_FINAL_ID = '9999999999999'
export const CONSUMIDOR_FINAL_NAME = 'CONSUMIDOR FINAL'

export const DOC_TYPE_LABELS: Record<string, string> = {
  '01': 'Factura',
  '04': 'Nota de Crédito',
}

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  PENDING: 'Pendiente',
  PROCESSING: 'En proceso',
  AUTHORIZED: 'Autorizado',
  REJECTED: 'Rechazado',
  FAILED: 'Falló (reintentando)',
  FAILED_PERMANENT: 'Falló definitivamente',
  ANNULLED: 'Anulado',
}

export const DOCUMENT_STATUS_BADGE_VARIANT: Record<DocumentStatus, BadgeVariant> = {
  PENDING: 'neutral',
  PROCESSING: 'primary',
  AUTHORIZED: 'success',
  REJECTED: 'error',
  FAILED: 'warning',
  FAILED_PERMANENT: 'error',
  ANNULLED: 'neutral',
}

export const DOCUMENT_STATUS_OPTIONS: Array<{ value: DocumentStatus | 'all'; label: string }> = [
  { value: 'all', label: 'Todos' },
  { value: 'PENDING', label: 'Pendiente' },
  { value: 'PROCESSING', label: 'En proceso' },
  { value: 'AUTHORIZED', label: 'Autorizado' },
  { value: 'REJECTED', label: 'Rechazado' },
  { value: 'FAILED', label: 'Falló' },
  { value: 'FAILED_PERMANENT', label: 'Falló definitivo' },
  { value: 'ANNULLED', label: 'Anulado' },
]

export const IVA_RATE_OPTIONS: Array<{ value: IvaRate; label: string }> = [
  { value: '15', label: '15%' },
  { value: '5', label: '5%' },
  { value: '0', label: '0%' },
  { value: 'EXENTO', label: 'Exento' },
]

export const BUYER_ID_TYPE_LABELS: Record<BuyerIdType, string> = {
  '04': 'RUC',
  '05': 'Cédula',
  '06': 'Pasaporte',
  '07': 'Consumidor Final',
  '08': 'Exterior',
}

export const PAYMENT_METHOD_OPTIONS: Array<{ value: PaymentMethod; label: string }> = [
  { value: '01', label: 'Efectivo' },
  { value: '16', label: 'Tarjeta de débito' },
  { value: '19', label: 'Tarjeta de crédito' },
  { value: '17', label: 'Dinero electrónico' },
  { value: '18', label: 'Tarjeta prepago' },
  { value: '15', label: 'Compensación de deudas' },
  { value: '20', label: 'Otro (sistema financiero)' },
  { value: '21', label: 'Endoso de títulos' },
]

export const BUYER_MODE_OPTIONS: Array<{ value: BuyerMode; label: string }> = [
  { value: 'consumidor_final', label: 'Consumidor Final' },
  { value: 'cliente', label: 'Cliente existente' },
]
