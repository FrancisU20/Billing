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
  PLAN_LIMIT_CYCLE_OPTIONS,
  PLAN_SEARCH_MODE_OPTIONS,
  PLAN_STATUS_OPTIONS,
} from '../constants'
import { clearPlanFilterField, planFilterChips, type PlanFilterDraft } from '../filters'

const LIMIT_CYCLE_OPTIONS = [{ value: 'all' as const, label: 'Todos' }, ...PLAN_LIMIT_CYCLE_OPTIONS]

interface PlansFiltersProps {
  value: PlanFilterDraft
  onChange: (value: PlanFilterDraft) => void
  onApply: () => void
  onReset: () => void
  onSearchApply?: (value: PlanFilterDraft) => void
}

export function PlansFilters({
  value,
  onChange,
  onApply,
  onReset,
  onSearchApply,
}: PlansFiltersProps) {
  const { semantic } = useTheme()
  const chips = planFilterChips(value).map((chip) => ({
    ...chip,
    onRemove: () => {
      const next = clearPlanFilterField(value, chip.key)
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
                stretch
                options={PLAN_STATUS_OPTIONS}
                value={value.status}
                onChange={(status) => onChange({ ...value, status })}
              />
            </FilterBlock>

            <FilterBlock label="Ciclo">
              <SegmentedControl
                stretch
                options={LIMIT_CYCLE_OPTIONS}
                value={value.limitCycle}
                onChange={(limitCycle) => onChange({ ...value, limitCycle })}
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
          options={PLAN_SEARCH_MODE_OPTIONS}
          value={value.searchMode}
          onChange={(searchMode) => onChange({ ...value, searchMode })}
        />
        <SearchInput
          leftIcon={value.searchMode === 'q' ? 'search-outline' : 'link-outline'}
          placeholder={value.searchMode === 'q' ? 'Nombre, descripción o slug' : 'basic'}
          autoCapitalize="none"
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
