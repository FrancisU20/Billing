import { emitCreditNoteSchema } from './schemas'
import { ecuadorIssuedAtDate } from './form'
import type {
  CreditNoteFormLine,
  Document,
  EmitCreditNoteFormValues,
  EmitCreditNoteInput,
} from './types'

/**
 * Pre-llena la pantalla de Nota de Credito al 100% del documento padre — el usuario
 * solo puede bajar cantidades (nunca subirlas ni agregar/quitar lineas), o nada en
 * absoluto si `locked` (entrada "Anular factura"). Campos propios, no se reusa
 * defaultEmitDocumentFormValues: la NC no tiene buyer-picking ni override de descuento.
 */
export function defaultCreditNoteFormValues(
  parent: Document,
  locked: boolean,
): EmitCreditNoteFormValues {
  return {
    establishment_code: parent.serie.slice(0, 3),
    emission_point_code: parent.serie.slice(3, 6),
    issued_at: ecuadorIssuedAtDate(),
    credit_note_reason: '',
    lines: parent.lines.map((line, index) => ({
      parent_line_index: index,
      code: line.code,
      description: line.description,
      unit_price: line.unit_price,
      iva_rate: line.iva_rate,
      original_quantity: line.quantity,
      original_subtotal: line.subtotal,
      original_iva_amount: line.iva_amount,
      quantity: line.quantity,
    })),
    locked,
  }
}

export function creditNoteFormValuesToInput(
  values: EmitCreditNoteFormValues,
  relatedDocumentId: string,
): EmitCreditNoteInput {
  return emitCreditNoteSchema.parse({
    establishment_code: values.establishment_code,
    emission_point_code: values.emission_point_code,
    doc_type: '04',
    issued_at: values.issued_at,
    related_document_id: relatedDocumentId,
    credit_note_reason: values.credit_note_reason.trim(),
    lines: values.lines.map((line) => ({
      parent_line_index: line.parent_line_index,
      quantity: line.quantity,
    })),
  })
}

export interface CreditNoteLinePreview {
  subtotal: number
  iva: number
  total: number
}

/**
 * Preview de una linea acreditada — escala los montos YA calculados de la linea
 * original por (cantidad acreditada / cantidad original), igual que
 * EmitCreditNoteUseCase._build_credit_lines (backend). Solo UX: el backend recalcula
 * todo desde la factura padre antes de emitir.
 */
export function computeCreditNoteLinePreview(line: CreditNoteFormLine): CreditNoteLinePreview {
  const originalQuantity = toNumber(line.original_quantity)
  const quantity = toNumber(line.quantity)
  const ratio = originalQuantity > 0 ? quantity / originalQuantity : 0
  const subtotal = round2(toNumber(line.original_subtotal) * ratio)
  const iva = round2(toNumber(line.original_iva_amount) * ratio)
  return { subtotal, iva, total: round2(subtotal + iva) }
}

export interface CreditNoteTotalsPreview {
  subtotal: number
  iva15: number
  iva5: number
  total: number
}

export function computeCreditNoteTotals(lines: CreditNoteFormLine[]): CreditNoteTotalsPreview {
  let subtotal = 0
  let iva15 = 0
  let iva5 = 0

  for (const line of lines) {
    const preview = computeCreditNoteLinePreview(line)
    subtotal += preview.subtotal
    if (line.iva_rate === '15') {
      iva15 += preview.iva
    } else if (line.iva_rate === '5') {
      iva5 += preview.iva
    }
  }

  subtotal = round2(subtotal)
  iva15 = round2(iva15)
  iva5 = round2(iva5)

  return { subtotal, iva15, iva5, total: round2(subtotal + iva15 + iva5) }
}

function toNumber(value: string): number {
  const n = parseFloat(value)
  return Number.isFinite(n) ? n : 0
}

function round2(value: number): number {
  return Math.round(value * 100) / 100
}
