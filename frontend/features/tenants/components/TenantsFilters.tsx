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
  TENANT_ENVIRONMENT_OPTIONS,
  TENANT_PLAN_STATUS_OPTIONS,
  TENANT_SEARCH_MODE_OPTIONS,
  TENANT_STATUS_OPTIONS,
} from '../constants'
import { clearTenantFilterField, tenantFilterChips, type TenantFilterDraft } from '../filters'

interface TenantsFiltersProps {
  value: TenantFilterDraft
  onChange: (value: TenantFilterDraft) => void
  onApply: () => void
  onReset: () => void
  onSearchApply?: (value: TenantFilterDraft) => void
}

export function TenantsFilters({
  value,
  onChange,
  onApply,
  onReset,
  onSearchApply,
}: TenantsFiltersProps) {
  const { semantic } = useTheme()
  const chips = tenantFilterChips(value).map((chip) => ({
    ...chip,
    onRemove: () => {
      const next = clearTenantFilterField(value, chip.key)
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
          <FilterBlock label="Estado">
            <SegmentedControl
              options={TENANT_STATUS_OPTIONS}
              value={value.status}
              onChange={(status) => onChange({ ...value, status })}
            />
          </FilterBlock>

          <View style={styles.grid}>
            <FilterBlock label="Entorno SRI">
              <SegmentedControl
                options={TENANT_ENVIRONMENT_OPTIONS}
                value={value.sriEnvironment}
                onChange={(sriEnvironment) => onChange({ ...value, sriEnvironment })}
              />
            </FilterBlock>

            <FilterBlock label="Plan">
              <View style={styles.pillGrid}>
                {TENANT_PLAN_STATUS_OPTIONS.map((option) => (
                  <FilterPill
                    key={option.value}
                    label={option.label}
                    selected={value.planStatus === option.value}
                    onPress={() => onChange({ ...value, planStatus: option.value })}
                  />
                ))}
              </View>
            </FilterBlock>
          </View>

          <FilterBlock label="Creación">
            <DateRangePicker
              from={value.createdFrom}
              to={value.createdTo}
              onChange={({ from, to }) => onChange({ ...value, createdFrom: from, createdTo: to })}
            />
          </FilterBlock>

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
          options={TENANT_SEARCH_MODE_OPTIONS}
          value={value.searchMode}
          onChange={(searchMode) => onChange({ ...value, searchMode })}
        />
        <SearchInput
          leftIcon={value.searchMode === 'q' ? 'search-outline' : 'card-outline'}
          placeholder={
            value.searchMode === 'q' ? 'Empresa, representante, email o RUC' : '1792146739001'
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
  actions: { alignItems: 'flex-start' },
})
