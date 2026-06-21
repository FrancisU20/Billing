import React from 'react'
import { FilterBar } from '@/components/ui/FilterBar'
import { FilterBlock } from '@/components/ui/FilterBlock'
import { SearchInput } from '@/components/ui/SearchInput'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { PRODUCT_KIND_OPTIONS } from '../constants'
import { clearProductFilterField, productFilterChips, type ProductFilterDraft } from '../filters'

interface ProductsFiltersProps {
  value: ProductFilterDraft
  onChange: (value: ProductFilterDraft) => void
  onApply: () => void
  onReset: () => void
  onSearchApply?: (value: ProductFilterDraft) => void
}

const KIND_OPTIONS = [{ value: 'all' as const, label: 'Todos' }, ...PRODUCT_KIND_OPTIONS]

export function ProductsFilters({
  value,
  onChange,
  onApply,
  onReset,
  onSearchApply,
}: ProductsFiltersProps) {
  const chips = productFilterChips(value).map((chip) => ({
    ...chip,
    onRemove: () => {
      const next = clearProductFilterField(value, chip.key)
      onChange(next)
      onSearchApply?.(next)
    },
  }))

  return (
    <FilterBar
      chips={chips}
      activeSecondaryCount={chips.length}
      onApply={onApply}
      onReset={onReset}
      secondaryContent={
        <FilterBlock label="Tipo">
          <SegmentedControl
            options={KIND_OPTIONS}
            value={value.kind}
            onChange={(kind) => onChange({ ...value, kind })}
          />
        </FilterBlock>
      }
    >
      <SearchInput
        leftIcon="search-outline"
        placeholder="Buscar por SKU, nombre o descripción"
        value={value.search}
        onChangeText={(search) => onChange({ ...value, search })}
        onSearchChange={(search) => onSearchApply?.({ ...value, search })}
        onSubmitEditing={onApply}
      />
    </FilterBar>
  )
}
