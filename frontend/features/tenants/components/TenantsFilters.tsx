import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import {
  TENANT_ENVIRONMENT_OPTIONS,
  TENANT_PLAN_STATUS_OPTIONS,
  TENANT_SEARCH_MODE_OPTIONS,
  TENANT_STATUS_OPTIONS,
  type TenantSearchMode,
} from '../constants'
import type { PlanStatus, SriEnvironment, TenantListFilters, TenantStatus } from '../types'

export interface TenantFilterDraft {
  searchMode: TenantSearchMode
  search: string
  status: TenantStatus | 'all'
  sriEnvironment: SriEnvironment | 'all'
  planStatus: PlanStatus | 'all'
  createdFrom: string
  createdTo: string
}

interface TenantsFiltersProps {
  value: TenantFilterDraft
  onChange: (value: TenantFilterDraft) => void
  onApply: () => void
  onReset: () => void
}

export const emptyTenantFilterDraft: TenantFilterDraft = {
  searchMode: 'q',
  search: '',
  status: 'all',
  sriEnvironment: 'all',
  planStatus: 'all',
  createdFrom: '',
  createdTo: '',
}

export function toTenantListFilters(value: TenantFilterDraft): TenantListFilters {
  const search = value.search.trim()
  return {
    q: value.searchMode === 'q' && search ? search : undefined,
    ruc: value.searchMode === 'ruc' && search ? search : undefined,
    status: value.status === 'all' ? undefined : value.status,
    sri_environment: value.sriEnvironment === 'all' ? undefined : value.sriEnvironment,
    plan_status: value.planStatus === 'all' ? undefined : value.planStatus,
    created_from: value.createdFrom.trim() || undefined,
    created_to: value.createdTo.trim() || undefined,
  }
}

export function TenantsFilters({ value, onChange, onApply, onReset }: TenantsFiltersProps) {
  const { semantic } = useTheme()

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.header}>
        <View style={styles.titleRow}>
          <Ionicons name="filter-outline" size={18} color={semantic.accent.default} />
          <Text style={[styles.title, { color: semantic.text.primary }]}>Filtros</Text>
        </View>
        <Pressable onPress={onReset} hitSlop={8} style={styles.resetButton}>
          <Ionicons name="refresh-outline" size={16} color={semantic.text.secondary} />
          <Text style={[styles.resetText, { color: semantic.text.secondary }]}>Limpiar</Text>
        </Pressable>
      </View>

      <View style={styles.section}>
        <Text style={[styles.label, { color: semantic.text.secondary }]}>Búsqueda</Text>
        <SegmentedControl
          options={TENANT_SEARCH_MODE_OPTIONS}
          value={value.searchMode}
          onChange={(searchMode) => onChange({ ...value, searchMode })}
        />
        <Input
          leftIcon={value.searchMode === 'q' ? 'search-outline' : 'card-outline'}
          placeholder={
            value.searchMode === 'q' ? 'Empresa, representante, email o RUC' : '1792146739001'
          }
          autoCapitalize="characters"
          value={value.search}
          onChangeText={(search) => onChange({ ...value, search })}
          onSubmitEditing={onApply}
        />
      </View>

      <View style={styles.grid}>
        <FilterBlock label="Estado">
          <SegmentedControl
            options={TENANT_STATUS_OPTIONS}
            value={value.status}
            onChange={(status) => onChange({ ...value, status })}
          />
        </FilterBlock>

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
    </View>
  )
}

function FilterBlock({ label, children }: { label: string; children: React.ReactNode }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.block}>
      <Text style={[styles.label, { color: semantic.text.secondary }]}>{label}</Text>
      {children}
    </View>
  )
}

function FilterPill({
  label,
  selected,
  onPress,
}: {
  label: string
  selected: boolean
  onPress: () => void
}) {
  const { semantic } = useTheme()
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.pill,
        {
          backgroundColor: selected
            ? semantic.accent.subtle
            : pressed
              ? semantic.bg.secondary
              : semantic.bg.primary,
          borderColor: selected ? semantic.accent.default : semantic.border.default,
        },
      ]}
    >
      <Text
        style={[
          styles.pillText,
          { color: selected ? semantic.accent.default : semantic.text.secondary },
        ]}
      >
        {label}
      </Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  container: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[4],
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing[3],
  },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  resetButton: { flexDirection: 'row', alignItems: 'center', gap: spacing[1] },
  resetText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  section: { gap: spacing[2] },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  block: { minWidth: 260, flex: 1, gap: spacing[2] },
  label: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  pillGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  pill: {
    alignItems: 'center',
    borderRadius: radius.full,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: spacing[3],
  },
  pillText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  dateRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  dateInput: { minWidth: 140, flex: 1 },
  actions: { alignItems: 'flex-start' },
})
