import { describe, expect, it } from 'vitest'
import {
  createProductSchema,
  discountCampaignSchema,
  productFormSchema,
  productSchema,
  updateDiscountCampaignSchema,
} from './schemas'
import { formValuesToCreateProductInput, defaultProductFormValues } from './form'

const product = {
  id: 'product-1',
  tenant_id: 'tenant-1',
  sku: 'PROD-001',
  invoice_code: 'PROD-001',
  name: 'Producto Demo',
  description: 'Producto de prueba',
  kind: 'PRODUCT',
  unit: 'unit',
  unit_price: '25.50',
  iva_rate: '15',
  discount_percentage: '15.50',
  stock_enabled: false,
  stock_quantity: null,
  low_stock_threshold: null,
  status: 'ACTIVE',
  created_at: '2026-06-08T00:00:00+00:00',
  updated_at: '2026-06-08T00:00:00+00:00',
  created_by: 'user-1',
  updated_by: 'user-1',
  version: '1',
} as const

// Matches the shape generateProductSku() produces (20 hex chars, well under the
// SRI 25-char limit for the document line code filled from a product's sku).
const generatedSku = '550E8400E29B41D4A716'

describe('product contract schemas', () => {
  it('accepts the backend product shape with a discount', () => {
    expect(productSchema.parse(product)).toEqual({ ...product, version: 1 })
  })

  it('accepts a product without discount (null)', () => {
    expect(productSchema.parse({ ...product, discount_percentage: null })).toEqual({
      ...product,
      discount_percentage: null,
      version: 1,
    })
  })

  it('defaults the form discount to an empty string when no product is provided', () => {
    expect(defaultProductFormValues().discount_percentage).toBe('')
  })

  it('pre-fills the form discount from an existing product', () => {
    expect(defaultProductFormValues({ ...product, version: 1 }).discount_percentage).toBe('15.50')
  })

  it('rejects a discount over 100%', () => {
    expect(() =>
      productFormSchema.parse({
        sku: 'PROD-001',
        name: 'Producto Demo',
        description: '',
        kind: 'PRODUCT',
        unit: 'unit',
        unit_price: '25.50',
        iva_rate: '15',
        discount_percentage: '100.01',
        stock_enabled: false,
        stock_quantity: '',
        low_stock_threshold: '',
        status: 'ACTIVE',
      }),
    ).toThrow()
  })

  it('accepts an auto-generated SKU', () => {
    const values = productFormSchema.parse({
      sku: generatedSku,
      name: 'Producto Demo',
      description: '',
      kind: 'PRODUCT',
      unit: 'unit',
      unit_price: '25.50',
      iva_rate: '15',
      discount_percentage: '',
      stock_enabled: false,
      stock_quantity: '',
      low_stock_threshold: '',
      status: 'ACTIVE',
    })

    expect(createProductSchema.parse(formValuesToCreateProductInput(values)).sku).toBe(generatedSku)
  })

  it('accepts a sku longer than the SRI 25-char invoice code limit', () => {
    // sku is the tenant's own free-form catalog code (here 30 chars) — the
    // backend derives a separate, SRI-compliant invoice_code from it, so the
    // form itself only needs to enforce its own (much larger) max length.
    const longSku = 'Repuesto Motor Diesel 2024 Ref'
    const values = productFormSchema.parse({
      sku: longSku,
      name: 'Producto Demo',
      description: '',
      kind: 'PRODUCT',
      unit: 'unit',
      unit_price: '25.50',
      iva_rate: '15',
      discount_percentage: '',
      stock_enabled: false,
      stock_quantity: '',
      low_stock_threshold: '',
      status: 'ACTIVE',
    })

    expect(values.sku).toBe(longSku)
  })

  it('rejects a sku over the 50-char form limit', () => {
    expect(() =>
      productFormSchema.parse({
        sku: 'A'.repeat(51),
        name: 'Producto Demo',
        description: '',
        kind: 'PRODUCT',
        unit: 'unit',
        unit_price: '25.50',
        iva_rate: '15',
        discount_percentage: '',
        stock_enabled: false,
        stock_quantity: '',
        low_stock_threshold: '',
        status: 'ACTIVE',
      }),
    ).toThrow()
  })

  it('builds the API payload with the discount as a string, or null when empty', () => {
    const values = productFormSchema.parse({
      sku: 'PROD-001',
      name: 'Producto Demo',
      description: '',
      kind: 'PRODUCT',
      unit: 'unit',
      unit_price: '25.50',
      iva_rate: '15',
      discount_percentage: '60',
      stock_enabled: false,
      stock_quantity: '',
      low_stock_threshold: '',
      status: 'ACTIVE',
    })

    expect(formValuesToCreateProductInput(values).discount_percentage).toBe('60')

    const withoutDiscount = productFormSchema.parse({ ...values, discount_percentage: '' })
    expect(formValuesToCreateProductInput(withoutDiscount).discount_percentage).toBeNull()
  })

  it('rejects an out-of-range discount at the payload boundary too', () => {
    expect(() =>
      createProductSchema.parse({
        sku: 'PROD-001',
        name: 'Producto Demo',
        description: '',
        kind: 'PRODUCT',
        unit: 'unit',
        unit_price: '25.50',
        iva_rate: '15',
        discount_percentage: 'not-a-number',
        stock_enabled: false,
      }),
    ).toThrow()
  })
})

describe('discount campaign contract schemas', () => {
  it('accepts the backend campaign shape', () => {
    expect(
      discountCampaignSchema.parse({
        active: true,
        percentage: '50.00',
        updated_at: '2026-06-19T00:00:00+00:00',
        updated_by: 'user-1',
        version: '3',
      }),
    ).toEqual({
      active: true,
      percentage: '50.00',
      updated_at: '2026-06-19T00:00:00+00:00',
      updated_by: 'user-1',
      version: 3,
    })
  })

  it('builds a valid update payload', () => {
    expect(updateDiscountCampaignSchema.parse({ active: true, percentage: '50' })).toEqual({
      active: true,
      percentage: '50',
    })
  })

  it('rejects a campaign percentage over 100', () => {
    expect(() =>
      updateDiscountCampaignSchema.parse({ active: true, percentage: '100.5' }),
    ).toThrow()
  })

  it('rejects a non-numeric campaign percentage', () => {
    expect(() =>
      updateDiscountCampaignSchema.parse({ active: true, percentage: 'fifty' }),
    ).toThrow()
  })
})
