import { describe, expect, it } from 'vitest'
import {
  computeLineTotals,
  defaultEmitDocumentFormValues,
  ecuadorIssuedAtDate,
  ecuadorIssuedAtDisplay,
} from './form'
import type { EmitDocumentLineInput } from './schemas'

describe('computeLineTotals', () => {
  it('computes subtotal, discount and IVA for a single 15% line', () => {
    const lines: EmitDocumentLineInput[] = [
      {
        code: 'P1',
        description: 'Producto 1',
        quantity: '2',
        unit_price: '10.00',
        discount: '0.00',
        iva_rate: '15',
      },
    ]

    expect(computeLineTotals(lines)).toEqual({
      subtotal: 20,
      totalDiscount: 0,
      iva15: 3,
      iva5: 0,
      total: 23,
    })
  })

  it('mixes IVA rates across lines and applies discount', () => {
    const lines: EmitDocumentLineInput[] = [
      {
        code: 'P1',
        description: 'Producto 1',
        quantity: '1',
        unit_price: '100.00',
        discount: '10.00',
        iva_rate: '15',
      },
      {
        code: 'P2',
        description: 'Producto 2',
        quantity: '3',
        unit_price: '20.00',
        discount: '0.00',
        iva_rate: '5',
      },
      {
        code: 'P3',
        description: 'Producto 3',
        quantity: '1',
        unit_price: '5.00',
        discount: '0.00',
        iva_rate: '0',
      },
      {
        code: 'P4',
        description: 'Producto 4',
        quantity: '1',
        unit_price: '8.00',
        discount: '0.00',
        iva_rate: 'EXENTO',
      },
    ]

    const totals = computeLineTotals(lines)

    // P1: 100 - 10 = 90 subtotal, IVA 15% = 13.5
    // P2: 60 subtotal, IVA 5% = 3
    // P3 + P4: 5 + 8 = 13 subtotal sin IVA
    expect(totals.subtotal).toBeCloseTo(90 + 60 + 5 + 8, 2)
    expect(totals.totalDiscount).toBe(10)
    expect(totals.iva15).toBeCloseTo(13.5, 2)
    expect(totals.iva5).toBeCloseTo(3, 2)
    expect(totals.total).toBeCloseTo(90 + 60 + 5 + 8 + 13.5 + 3, 2)
  })

  it('treats invalid numeric strings as zero instead of NaN', () => {
    const lines: EmitDocumentLineInput[] = [
      {
        code: 'P1',
        description: 'Producto 1',
        quantity: '',
        unit_price: '',
        discount: '',
        iva_rate: '15',
      },
    ]

    expect(computeLineTotals(lines)).toEqual({
      subtotal: 0,
      totalDiscount: 0,
      iva15: 0,
      iva5: 0,
      total: 0,
    })
  })

  it('returns zero totals for an empty list of lines', () => {
    expect(computeLineTotals([])).toEqual({
      subtotal: 0,
      totalDiscount: 0,
      iva15: 0,
      iva5: 0,
      total: 0,
    })
  })
})

describe('defaultEmitDocumentFormValues', () => {
  it('defaults to Consumidor Final with one empty line', () => {
    const values = defaultEmitDocumentFormValues('001', '001')

    expect(values.establishment_code).toBe('001')
    expect(values.emission_point_code).toBe('001')
    expect(values.buyer_mode).toBe('consumidor_final')
    expect(values.buyer_id_type).toBe('07')
    expect(values.buyer_id).toBe('9999999999999')
    expect(values.buyer_name).toBe('Consumidor Final')
    expect(values.client_id).toBeNull()
    expect(values.lines).toHaveLength(1)
  })
})

describe('Ecuador issued_at helpers', () => {
  it('uses America/Guayaquil date instead of UTC date', () => {
    const now = new Date('2026-06-19T00:04:00.000Z')

    expect(ecuadorIssuedAtDate(now)).toBe('2026-06-18')
    expect(ecuadorIssuedAtDisplay(now)).toBe('18/06/2026 19:04')
  })
})
