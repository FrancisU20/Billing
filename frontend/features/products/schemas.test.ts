import { describe, expect, it } from 'vitest'
import { createProductSchema, productFormSchema, productSchema } from './schemas'
import { formValuesToCreateProductInput, defaultProductFormValues } from './form'

const product = {
  id: 'product-1',
  tenant_id: 'tenant-1',
  sku: 'PROD-001',
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
