import { describe, expect, it } from 'vitest'
import { generateProductSku } from './sku'

// SRI caps the document line code (codigoPrincipal/codigoAuxiliar) filled from a
// product's sku at 25 chars, so the generated SKU must always fit under that.
const SKU_RE = /^[0-9A-F]{20}$/

describe('product SKU generation', () => {
  it('generates an uppercase hex SKU that fits the SRI 25-char limit', () => {
    const sku = generateProductSku()

    expect(sku).toMatch(SKU_RE)
    expect(sku.length).toBeLessThanOrEqual(25)
  })

  it('generates different SKUs across calls', () => {
    expect(generateProductSku()).not.toBe(generateProductSku())
  })
})
