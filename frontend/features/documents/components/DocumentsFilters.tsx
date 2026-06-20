import React from 'react'
import { StyleSheet, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { DateRangePicker } from '@/components/ui/DateRangePicker'
import { FilterBar } from '@/components/ui/FilterBar'
import { FilterBlock, FilterPill } from '@/components/ui/FilterBlock'
import { SearchInput } from '@/components/ui/SearchInput'
import { spacing } from '@/constants/tokens'
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
      onReset={onReset}
      secondaryContent={
        <>
          <View style={styles.grid}>
            <FilterBlock label="Estado">
              <View style={styles.pillGrid}>
                {DOCUMENT_STATUS_OPTIONS.map((option) => (
                  <FilterPill
                    key={option.value}
                    label={option.label}
                    selected={value.status === option.value}
                    onPress={() => onChange({ ...value, status: option.value })}
                  />
                ))}
              </View>
            </FilterBlock>

            <FilterBlock label="Emisión">
              <DateRangePicker
                from={value.dateFrom}
                to={value.dateTo}
                onChange={({ from, to }) => onChange({ ...value, dateFrom: from, dateTo: to })}
              />
            </FilterBlock>
          </View>

          <View style={styles.actions}>
            <Button variant="primary" size="md" onPress={onApply}>
              Aplicar filtros
            </Button>
          </View>
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

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  pillGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { alignItems: 'flex-start' },
})
