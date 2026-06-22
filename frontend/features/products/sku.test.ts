import { describe, expect, it } from 'vitest'
import { generateProductSku } from './sku'

const UUID_V4_RE = /^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/

describe('product SKU generation', () => {
  it('generates an uppercase UUID v4 SKU', () => {
    const sku = generateProductSku()

    expect(sku).toMatch(UUID_V4_RE)
    expect(sku).toHaveLength(36)
  })

  it('generates different SKUs across calls', () => {
    expect(generateProductSku()).not.toBe(generateProductSku())
  })
})
