import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { FilterBar } from '@/components/ui/FilterBar'
import { FilterBlock, FilterPill } from '@/components/ui/FilterBlock'
import { Input } from '@/components/ui/Input'
import { SearchInput } from '@/components/ui/SearchInput'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'
import {
  CLIENT_IDENTIFICATION_LABELS,
  CLIENT_IDENTIFICATION_OPTIONS,
  CLIENT_SEARCH_MODE_OPTIONS,
  CLIENT_STATUS_OPTIONS,
} from '../constants'
import { clearClientFilterField, clientFilterChips, type ClientFilterDraft } from '../filters'

interface ClientsFiltersProps {
  value: ClientFilterDraft
  onChange: (value: ClientFilterDraft) => void
  onApply: () => void
  onReset: () => void
  onSearchApply?: (value: ClientFilterDraft) => void
}

export function ClientsFilters({
  value,
  onChange,
  onApply,
  onReset,
  onSearchApply,
}: ClientsFiltersProps) {
  const { semantic } = useTheme()
  const chips = clientFilterChips(value).map((chip) => ({
    ...chip,
    onRemove: () => {
      const next = clearClientFilterField(value, chip.key)
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
              <SegmentedControl
                options={CLIENT_STATUS_OPTIONS}
                value={value.status}
                onChange={(status) => onChange({ ...value, status })}
              />
            </FilterBlock>

            <FilterBlock label="Tipo">
              <View style={styles.pillGrid}>
                <FilterPill
                  label="Todos"
                  selected={value.identificationType === 'all'}
                  onPress={() => onChange({ ...value, identificationType: 'all' })}
                />
                {CLIENT_IDENTIFICATION_OPTIONS.map((option) => (
                  <FilterPill
                    key={option.value}
                    label={CLIENT_IDENTIFICATION_LABELS[option.value]}
                    selected={value.identificationType === option.value}
                    onPress={() => onChange({ ...value, identificationType: option.value })}
                  />
                ))}
              </View>
            </FilterBlock>

            <FilterBlock label="Creación">
              <View style={styles.dateRow}>
                <View style={styles.dateInput}>
                  <Input
                    leftIcon="calendar-outline"
                    placeholder="Desde"
                    value={value.createdFrom}
                    onChangeText={(createdFrom) => onChange({ ...value, createdFrom })}
                    onSubmitEditing={onApply}
                  />
                </View>
                <View style={styles.dateInput}>
                  <Input
                    leftIcon="calendar-outline"
                    placeholder="Hasta"
                    value={value.createdTo}
                    onChangeText={(createdTo) => onChange({ ...value, createdTo })}
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
      <View style={styles.section}>
        <Text style={[styles.label, { color: semantic.text.secondary }]}>Búsqueda</Text>
        <SegmentedControl
          options={CLIENT_SEARCH_MODE_OPTIONS}
          value={value.searchMode}
          onChange={(searchMode) => onChange({ ...value, searchMode })}
        />
        <SearchInput
          leftIcon={value.searchMode === 'q' ? 'search-outline' : 'card-outline'}
          placeholder={
            value.searchMode === 'q'
              ? 'Razón social, nombre comercial o identificación'
              : '1792146739001'
          }
          autoCapitalize="characters"
          value={value.search}
          onChangeText={(search) => onChange({ ...value, search })}
          onSearchChange={(search) => onSearchApply?.({ ...value, search })}
          onSubmitEditing={onApply}
        />
      </View>
    </FilterBar>
  )
}

const styles = StyleSheet.create({
  section: { gap: spacing[2] },
  label: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  pillGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  dateRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  dateInput: { minWidth: 140, flex: 1 },
  actions: { alignItems: 'flex-start' },
})
