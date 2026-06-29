import { describe, expect, it } from 'vitest'
import { computeCreditNoteLinePreview, computeCreditNoteTotals } from './creditNoteForm'
import type { CreditNoteFormLine } from './types'

function line(overrides: Partial<CreditNoteFormLine> = {}): CreditNoteFormLine {
  return {
    parent_line_index: 0,
    code: 'P1',
    description: 'Producto 1',
    unit_price: '10.00',
    iva_rate: '15',
    original_quantity: '4',
    original_subtotal: '38.00',
    original_iva_amount: '5.70',
    quantity: '1',
    ...overrides,
  }
}

describe('computeCreditNoteLinePreview', () => {
  it('scales already persisted parent invoice amounts', () => {
    expect(computeCreditNoteLinePreview(line())).toEqual({
      subtotal: 9.5,
      iva: 1.42,
      total: 10.92,
    })
  })

  it('treats invalid numeric strings as zero instead of NaN', () => {
    expect(
      computeCreditNoteLinePreview(
        line({
          original_quantity: '',
          original_subtotal: '',
          original_iva_amount: '',
          quantity: '',
        }),
      ),
    ).toEqual({
      subtotal: 0,
      iva: 0,
      total: 0,
    })
  })
})

describe('computeCreditNoteTotals', () => {
  it('aggregates IVA buckets and zero-rate lines', () => {
    expect(
      computeCreditNoteTotals([
        line(),
        line({
          parent_line_index: 1,
          iva_rate: '5',
          original_quantity: '2',
          original_subtotal: '20.00',
          original_iva_amount: '1.00',
          quantity: '2',
        }),
        line({
          parent_line_index: 2,
          iva_rate: '0',
          original_quantity: '1',
          original_subtotal: '8.00',
          original_iva_amount: '0.00',
          quantity: '1',
        }),
      ]),
    ).toEqual({
      subtotal: 37.5,
      iva15: 1.42,
      iva5: 1,
      total: 39.92,
    })
  })
})
