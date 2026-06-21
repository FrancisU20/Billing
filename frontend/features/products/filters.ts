import { productKindLabel } from './constants'
import type { ProductKind } from './schemas'
import type { ProductListFilters } from './types'

export interface ProductFilterDraft {
  search: string
  kind: ProductKind | 'all'
}

export const emptyProductFilterDraft: ProductFilterDraft = {
  search: '',
  kind: 'all',
}

export function toProductListFilters(value: ProductFilterDraft): ProductListFilters {
  const search = value.search.trim()
  return {
    q: search.length >= 3 ? search : undefined,
    kind: value.kind === 'all' ? undefined : value.kind,
  }
}

export interface ProductFilterChip {
  key: 'kind'
  label: string
}

export function productFilterChips(value: ProductFilterDraft): ProductFilterChip[] {
  const chips: ProductFilterChip[] = []
  if (value.kind !== 'all') {
    chips.push({ key: 'kind', label: `Tipo: ${productKindLabel(value.kind)}` })
  }
  return chips
}

export function clearProductFilterField(
  value: ProductFilterDraft,
  key: ProductFilterChip['key'],
): ProductFilterDraft {
  switch (key) {
    case 'kind':
      return { ...value, kind: 'all' }
  }
}
