import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { DOCUMENT_STATUS_OPTIONS } from '../constants'
import type { DocumentListFilters, DocumentStatus } from '../types'

export interface DocumentFilterDraft {
  status: DocumentStatus | 'all'
  serie: string
  dateFrom: string
  dateTo: string
}

export const emptyDocumentFilterDraft: DocumentFilterDraft = {
  status: 'all',
  serie: '',
  dateFrom: '',
  dateTo: '',
}

export function toDocumentListFilters(value: DocumentFilterDraft): DocumentListFilters {
  return {
    status: value.status === 'all' ? undefined : value.status,
    serie: value.serie.trim() || undefined,
    date_from: value.dateFrom.trim() || undefined,
    date_to: value.dateTo.trim() || undefined,
  }
}

interface DocumentsFiltersProps {
  value: DocumentFilterDraft
  onChange: (value: DocumentFilterDraft) => void
  onApply: () => void
  onReset: () => void
}

export function DocumentsFilters({ value, onChange, onApply, onReset }: DocumentsFiltersProps) {
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

      <View style={styles.grid}>
        <View style={styles.block}>
          <Text style={[styles.label, { color: semantic.text.secondary }]}>Estado</Text>
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
        </View>

        <View style={styles.block}>
          <Text style={[styles.label, { color: semantic.text.secondary }]}>Serie</Text>
          <Input
            leftIcon="pricetag-outline"
            placeholder="001001"
            value={value.serie}
            onChangeText={(serie) => onChange({ ...value, serie })}
            onSubmitEditing={onApply}
          />
        </View>

        <View style={styles.block}>
          <Text style={[styles.label, { color: semantic.text.secondary }]}>Emisión</Text>
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
        </View>
      </View>

      <View style={styles.actions}>
        <Button variant="primary" size="md" onPress={onApply}>
          Aplicar filtros
        </Button>
      </View>
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
  container: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[4] },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing[3],
  },
  titleRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  resetButton: { alignItems: 'center', flexDirection: 'row', gap: spacing[1] },
  resetText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  block: { flex: 1, gap: spacing[2], minWidth: 240 },
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
  dateInput: { flex: 1, minWidth: 140 },
  actions: { alignItems: 'flex-start' },
})
