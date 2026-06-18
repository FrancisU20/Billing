import { createProductSchema, updateProductSchema } from './schemas'
import type { CreateProductInput, Product, ProductFormValues, UpdateProductInput } from './types'

export function defaultProductFormValues(product?: Product): ProductFormValues {
  return {
    sku: product?.sku ?? '',
    name: product?.name ?? '',
    description: product?.description ?? '',
    kind: product?.kind ?? 'PRODUCT',
    unit: product?.unit ?? 'unit',
    unit_price: product?.unit_price ?? '0.00',
    iva_rate: product?.iva_rate ?? '15',
    stock_enabled: product?.stock_enabled ?? false,
    stock_quantity: product?.stock_quantity ?? '',
    low_stock_threshold: product?.low_stock_threshold ?? '',
    status: product?.status ?? 'ACTIVE',
  }
}

export function formValuesToCreateProductInput(values: ProductFormValues): CreateProductInput {
  return createProductSchema.parse({
    sku: values.sku.trim(),
    name: values.name.trim(),
    description: values.description.trim(),
    kind: values.kind,
    unit: values.unit.trim(),
    unit_price: values.unit_price.trim(),
    iva_rate: values.iva_rate,
    stock_enabled: values.stock_enabled,
    stock_quantity: values.stock_enabled ? values.stock_quantity.trim() || null : null,
    low_stock_threshold: values.stock_enabled ? values.low_stock_threshold.trim() || null : null,
  })
}

export function formValuesToUpdateProductInput(values: ProductFormValues): UpdateProductInput {
  return updateProductSchema.parse({
    ...formValuesToCreateProductInput(values),
    status: values.status,
  })
}
