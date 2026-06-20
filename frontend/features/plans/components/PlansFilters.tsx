import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { DateRangePicker } from '@/components/ui/DateRangePicker'
import { FilterBar } from '@/components/ui/FilterBar'
import { FilterBlock, FilterPill } from '@/components/ui/FilterBlock'
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
      onReset={onReset}
      secondaryContent={
        <>
          <View style={styles.grid}>
            <FilterBlock label="Estado">
              <SegmentedControl
                options={PLAN_STATUS_OPTIONS}
                value={value.status}
                onChange={(status) => onChange({ ...value, status })}
              />
            </FilterBlock>

            <FilterBlock label="Ciclo">
              <View style={styles.pillGrid}>
                <FilterPill
                  label="Todos"
                  selected={value.limitCycle === 'all'}
                  onPress={() => onChange({ ...value, limitCycle: 'all' })}
                />
                {PLAN_LIMIT_CYCLE_OPTIONS.map((option) => (
                  <FilterPill
                    key={option.value}
                    label={option.label}
                    selected={value.limitCycle === option.value}
                    onPress={() => onChange({ ...value, limitCycle: option.value })}
                  />
                ))}
              </View>
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
  pillGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { alignItems: 'flex-start' },
})
