import { describe, expect, it } from 'vitest'
import {
  computeLineTotals,
  defaultEmitDocumentFormValues,
  ecuadorIssuedAtDate,
  ecuadorIssuedAtDisplay,
  resolveDiscountPolicy,
  resolveSuggestedDiscount,
  shouldAutoApplySuggestedDiscount,
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
  it('defaults to Consumidor Final with no lines until a product is scanned or picked', () => {
    const values = defaultEmitDocumentFormValues('001', '001')

    expect(values.establishment_code).toBe('001')
    expect(values.emission_point_code).toBe('001')
    expect(values.buyer_mode).toBe('consumidor_final')
    expect(values.buyer_id_type).toBe('07')
    expect(values.buyer_id).toBe('9999999999999')
    expect(values.buyer_name).toBe('CONSUMIDOR FINAL')
    expect(values.client_id).toBeNull()
    expect(values.lines).toHaveLength(0)
    expect(values.override_discount_ceiling).toBe(false)
    expect(values.override_reason).toBe('')
  })
})

describe('resolveSuggestedDiscount', () => {
  it('returns 0 when there is no product discount and no active campaign', () => {
    expect(resolveSuggestedDiscount('1', '30.00', null, null)).toBe('0.00')
  })

  it('suggests the product discount percentage applied to the line gross', () => {
    expect(resolveSuggestedDiscount('1', '30.00', '60.00', null)).toBe('18.00')
  })

  it('suggests the campaign percentage when active and no product discount', () => {
    expect(
      resolveSuggestedDiscount('1', '100.00', null, { active: true, percentage: '50.00' }),
    ).toBe('50.00')
  })

  it('ignores the campaign percentage when inactive', () => {
    expect(
      resolveSuggestedDiscount('1', '100.00', null, { active: false, percentage: '50.00' }),
    ).toBe('0.00')
  })

  it('uses the higher of product % and campaign %, never their sum', () => {
    expect(
      resolveSuggestedDiscount('1', '30.00', '60.00', { active: true, percentage: '30.00' }),
    ).toBe('18.00')
  })

  it('scales with quantity', () => {
    expect(resolveSuggestedDiscount('2', '30.00', '60.00', null)).toBe('36.00')
  })

  it('returns 0 for an invalid or zero gross amount', () => {
    expect(resolveSuggestedDiscount('0', '30.00', '60.00', null)).toBe('0.00')
    expect(resolveSuggestedDiscount('', '', '60.00', null)).toBe('0.00')
  })
})

describe('resolveDiscountPolicy', () => {
  it('describes no discount when there is no product or active campaign percentage', () => {
    expect(resolveDiscountPolicy('1', '100.00', null, null)).toEqual({
      amount: '0.00',
      percentage: 0,
      source: 'none',
      label: 'Sin descuento',
    })
  })

  it('uses product discount when it is higher than campaign', () => {
    expect(
      resolveDiscountPolicy('2', '50.00', '15.00', { active: true, percentage: '10.00' }),
    ).toEqual({
      amount: '15.00',
      percentage: 15,
      source: 'product',
      label: 'Catálogo',
    })
  })

  it('uses active campaign when it is higher than product discount', () => {
    expect(
      resolveDiscountPolicy('1', '80.00', '5.00', { active: true, percentage: '12.50' }),
    ).toEqual({
      amount: '10.00',
      percentage: 12.5,
      source: 'campaign',
      label: 'Campaña',
    })
  })
})

describe('shouldAutoApplySuggestedDiscount', () => {
  it('applies a new suggestion when the current discount is zero', () => {
    expect(shouldAutoApplySuggestedDiscount('0.00', undefined, '10.00')).toBe(true)
  })

  it('updates a discount previously applied by the system', () => {
    expect(shouldAutoApplySuggestedDiscount('10.00', '10.00', '12.00')).toBe(true)
  })

  it('does not override a manual discount', () => {
    expect(shouldAutoApplySuggestedDiscount('7.00', '10.00', '12.00')).toBe(false)
  })

  it('clears a previous system suggestion when the next suggestion is zero', () => {
    expect(shouldAutoApplySuggestedDiscount('10.00', '10.00', '0.00')).toBe(true)
  })
})

describe('Ecuador issued_at helpers', () => {
  it('uses America/Guayaquil date instead of UTC date', () => {
    const now = new Date('2026-06-19T00:04:00.000Z')

    expect(ecuadorIssuedAtDate(now)).toBe('2026-06-18')
    expect(ecuadorIssuedAtDisplay(now)).toBe('18/06/2026 19:04')
  })
})
