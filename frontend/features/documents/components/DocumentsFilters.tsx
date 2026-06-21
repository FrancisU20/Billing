import React from 'react'
import { DateRangePicker } from '@/components/ui/DateRangePicker'
import { FilterBar } from '@/components/ui/FilterBar'
import { FilterBlock } from '@/components/ui/FilterBlock'
import { SearchInput } from '@/components/ui/SearchInput'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { DOCUMENT_STATUS_OPTIONS } from '../constants'
import { clearDocumentFilterField, documentFilterChips, type DocumentFilterDraft } from '../filters'

interface DocumentsFiltersProps {
  value: DocumentFilterDraft
  onChange: (value: DocumentFilterDraft) => void
  onApply: () => void
  onReset: () => void
  onSearchApply?: (value: DocumentFilterDraft) => void
}

export function DocumentsFilters({
  value,
  onChange,
  onApply,
  onReset,
  onSearchApply,
}: DocumentsFiltersProps) {
  const chips = documentFilterChips(value).map((chip) => ({
    ...chip,
    onRemove: () => {
      const next = clearDocumentFilterField(value, chip.key)
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
        <>
          <FilterBlock label="Estado">
            <SegmentedControl
              options={DOCUMENT_STATUS_OPTIONS}
              value={value.status}
              onChange={(status) => onChange({ ...value, status })}
            />
          </FilterBlock>

          <FilterBlock label="Emisión">
            <DateRangePicker
              from={value.dateFrom}
              to={value.dateTo}
              onChange={({ from, to }) => onChange({ ...value, dateFrom: from, dateTo: to })}
            />
          </FilterBlock>
        </>
      }
    >
      <SearchInput
        leftIcon="search-outline"
        placeholder="Serie, cédula/RUC o nombre"
        value={value.search}
        onChangeText={(search) => onChange({ ...value, search })}
        onSearchChange={(search) => onSearchApply?.({ ...value, search })}
        onSubmitEditing={onApply}
      />
    </FilterBar>
  )
}
