import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { DateRangePicker } from '@/components/ui/DateRangePicker'
import { FilterBar } from '@/components/ui/FilterBar'
import { FilterBlock } from '@/components/ui/FilterBlock'
import { SearchInput } from '@/components/ui/SearchInput'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'
import {
  CLIENT_IDENTIFICATION_OPTIONS,
  CLIENT_SEARCH_MODE_OPTIONS,
  CLIENT_STATUS_OPTIONS,
} from '../constants'
import { clearClientFilterField, clientFilterChips, type ClientFilterDraft } from '../filters'

const IDENTIFICATION_TYPE_OPTIONS = [
  { value: 'all' as const, label: 'Todos' },
  ...CLIENT_IDENTIFICATION_OPTIONS,
]

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
      onApply={onApply}
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
              <SegmentedControl
                options={IDENTIFICATION_TYPE_OPTIONS}
                value={value.identificationType}
                onChange={(identificationType) => onChange({ ...value, identificationType })}
              />
            </FilterBlock>

            <FilterBlock label="Creación">
              <DateRangePicker
                from={value.createdFrom}
                to={value.createdTo}
                onChange={({ from, to }) =>
                  onChange({ ...value, createdFrom: from, createdTo: to })
                }
              />
            </FilterBlock>
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
})
