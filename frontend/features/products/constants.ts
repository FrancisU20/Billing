import type { ProductKind, ProductStatus } from './types'

export const PRODUCTS_PAGE_SIZE = 20

export const PRODUCT_KIND_OPTIONS: Array<{ value: ProductKind; label: string }> = [
  { value: 'PRODUCT', label: 'Producto' },
  { value: 'SERVICE', label: 'Servicio' },
  { value: 'PACKAGE', label: 'Paquete' },
  { value: 'MEMBERSHIP', label: 'Membresía' },
  { value: 'OTHER', label: 'Otro' },
]

export const PRODUCT_STATUS_OPTIONS: Array<{ value: ProductStatus; label: string }> = [
  { value: 'ACTIVE', label: 'Activo' },
  { value: 'INACTIVE', label: 'Inactivo' },
]

export const PRODUCT_UNIT_OPTIONS = [
  { value: 'unit', label: 'Unidad' },
  { value: 'service', label: 'Servicio' },
  { value: 'hour', label: 'Hora' },
  { value: 'day', label: 'Día' },
  { value: 'month', label: 'Mes' },
  { value: 'package', label: 'Paquete' },
] as const

export function productKindLabel(kind: ProductKind): string {
  return PRODUCT_KIND_OPTIONS.find((option) => option.value === kind)?.label ?? kind
}

export function productStatusLabel(status: ProductStatus): string {
  return PRODUCT_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status
}
