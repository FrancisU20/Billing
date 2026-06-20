import React from 'react'
import { StyleSheet, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { FilterBar } from '@/components/ui/FilterBar'
import { FilterBlock, FilterPill } from '@/components/ui/FilterBlock'
import { Input } from '@/components/ui/Input'
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
              <View style={styles.dateRow}>
                <View style={styles.dateInput}>
                  <Input
                    leftIcon="calendar-outline"
                    placeholder="Desde"
                    value={value.dateFrom}
                    onChangeText={(dateFrom) => onChange({ ...value, dateFrom })}
                    onSubmitEditing={onApply}
                  />
                </View>
                <View style={styles.dateInput}>
                  <Input
                    leftIcon="calendar-outline"
                    placeholder="Hasta"
                    value={value.dateTo}
                    onChangeText={(dateTo) => onChange({ ...value, dateTo })}
                    onSubmitEditing={onApply}
                  />
                </View>
              </View>
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
        leftIcon="pricetag-outline"
        placeholder="Buscar por serie (001001)"
        value={value.serie}
        onChangeText={(serie) => onChange({ ...value, serie })}
        onSearchChange={(serie) => onSearchApply?.({ ...value, serie })}
        onSubmitEditing={onApply}
      />
    </FilterBar>
  )
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  pillGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  dateRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  dateInput: { flex: 1, minWidth: 140 },
  actions: { alignItems: 'flex-start' },
})
