import { emitDocumentSchema } from './schemas'
import { CONSUMIDOR_FINAL_ID, CONSUMIDOR_FINAL_ID_TYPE, CONSUMIDOR_FINAL_NAME } from './constants'
import type { EmitDocumentFormValues, EmitDocumentInput, EmitDocumentLineInput } from './types'

export function defaultEmitDocumentLine(): EmitDocumentLineInput {
  return {
    product_id: null,
    code: '',
    description: '',
    quantity: '1',
    unit_price: '0.00',
    discount: '0.00',
    iva_rate: '15',
  }
}

export function defaultEmitDocumentFormValues(
  establishmentCode: string,
  emissionPointCode: string,
): EmitDocumentFormValues {
  const today = new Date().toISOString().slice(0, 10)
  return {
    establishment_code: establishmentCode,
    emission_point_code: emissionPointCode,
    issued_at: today,
    buyer_mode: 'consumidor_final',
    client_id: null,
    buyer_id_type: CONSUMIDOR_FINAL_ID_TYPE,
    buyer_id: CONSUMIDOR_FINAL_ID,
    buyer_name: CONSUMIDOR_FINAL_NAME,
    buyer_email: '',
    payment_method: '01',
    lines: [defaultEmitDocumentLine()],
  }
}

export function formValuesToEmitDocumentInput(values: EmitDocumentFormValues): EmitDocumentInput {
  return emitDocumentSchema.parse({
    establishment_code: values.establishment_code,
    emission_point_code: values.emission_point_code,
    doc_type: '01',
    issued_at: values.issued_at,
    client_id: values.client_id,
    buyer_id_type: values.buyer_id_type,
    buyer_id: values.buyer_id.trim(),
    buyer_name: values.buyer_name.trim(),
    buyer_email: values.buyer_email.trim() || null,
    payment_method: values.payment_method,
    lines: values.lines,
  })
}

export interface LineTotalsPreview {
  subtotal: number
  totalDiscount: number
  iva15: number
  iva5: number
  total: number
}

function toNumber(value: string): number {
  const n = parseFloat(value)
  return Number.isFinite(n) ? n : 0
}

function round2(value: number): number {
  return Math.round(value * 100) / 100
}

/**
 * Preview de totales en el cliente — réplica de
 * `EmitDocumentUseCase._compute_totals` (backend) solo para UX antes de
 * emitir. El backend recalcula con `Decimal` y es la fuente de verdad final.
 */
export function computeLineTotals(lines: EmitDocumentLineInput[]): LineTotalsPreview {
  let subtotal = 0
  let totalDiscount = 0
  let iva15 = 0
  let iva5 = 0

  for (const line of lines) {
    const quantity = toNumber(line.quantity)
    const unitPrice = toNumber(line.unit_price)
    const discount = toNumber(line.discount)
    const lineSubtotal = round2(quantity * unitPrice - discount)

    subtotal += lineSubtotal
    totalDiscount += discount

    if (line.iva_rate === '15') {
      iva15 += round2((lineSubtotal * 15) / 100)
    } else if (line.iva_rate === '5') {
      iva5 += round2((lineSubtotal * 5) / 100)
    }
  }

  subtotal = round2(subtotal)
  totalDiscount = round2(totalDiscount)
  iva15 = round2(iva15)
  iva5 = round2(iva5)

  return { subtotal, totalDiscount, iva15, iva5, total: round2(subtotal + iva15 + iva5) }
}
