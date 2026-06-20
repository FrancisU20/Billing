import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { PAGE_SIZE_OPTIONS, type PageSize } from '@/constants/pagination'
import { radius, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'

interface ListPaginationControlsProps {
  page: number
  pageSize: PageSize
  itemCount: number
  canGoPrevious: boolean
  canGoNext: boolean
  loading?: boolean
  onPrevious: () => void
  onNext: () => void
  onPageSizeChange: (pageSize: PageSize) => void
  totalItems?: number | null
  totalPages?: number | null
}

export function ListPaginationControls({
  page,
  pageSize,
  itemCount,
  canGoPrevious,
  canGoNext,
  loading = false,
  onPrevious,
  onNext,
  onPageSizeChange,
  totalItems,
  totalPages,
}: ListPaginationControlsProps) {
  const { semantic } = useTheme()
  const hasTotal = totalItems != null && totalPages != null

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.summary}>
        <Text style={[styles.pageLabel, { color: semantic.text.primary }]}>
          {hasTotal ? `Página ${page} de ${totalPages}` : `Página ${page}`}
        </Text>
        <Text style={[styles.countLabel, { color: semantic.text.secondary }]}>
          {hasTotal
            ? `${totalItems} ${totalItems === 1 ? 'resultado' : 'resultados'} en total`
            : `${itemCount} registros en esta página`}
        </Text>
      </View>

      <View style={styles.controls}>
        <PageSizeSelector value={pageSize} onChange={onPageSizeChange} />
        <View style={styles.pageButtons}>
          <Button
            variant="outline"
            size="sm"
            isDisabled={loading || !canGoPrevious}
            onPress={onPrevious}
          >
            Anterior
          </Button>
          <Button variant="outline" size="sm" isDisabled={loading || !canGoNext} onPress={onNext}>
            Siguiente
          </Button>
        </View>
      </View>
    </View>
  )
}

function PageSizeSelector({
  value,
  onChange,
}: {
  value: PageSize
  onChange: (pageSize: PageSize) => void
}) {
  const { semantic } = useTheme()

  return (
    <View style={styles.pageSizeGroup}>
      <Ionicons name="list-outline" size={16} color={semantic.text.secondary} />
      <Text style={[styles.pageSizeLabel, { color: semantic.text.secondary }]}>Mostrar</Text>
      <View style={styles.pageSizeOptions}>
        {PAGE_SIZE_OPTIONS.map((option) => {
          const selected = option === value
          return (
            <Pressable
              key={option}
              accessibilityRole="button"
              accessibilityLabel={`Mostrar ${option} registros por página`}
              onPress={() => onChange(option)}
              style={({ pressed }) => [
                styles.pageSizeOption,
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
                  styles.pageSizeValue,
                  { color: selected ? semantic.accent.default : semantic.text.secondary },
                ]}
              >
                {option}
              </Text>
            </Pressable>
          )
        })}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
    justifyContent: 'space-between',
    padding: spacing[3],
  },
  summary: { gap: spacing[1] - 2 },
  pageLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  countLabel: { fontSize: typography.size.xs },
  controls: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[3],
  },
  pageButtons: { flexDirection: 'row', gap: spacing[2] },
  pageSizeGroup: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  pageSizeLabel: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  pageSizeOptions: { flexDirection: 'row', gap: spacing[1] },
  pageSizeOption: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    minHeight: 30,
    minWidth: 36,
    justifyContent: 'center',
    paddingHorizontal: spacing[2],
  },
  pageSizeValue: { fontSize: typography.size.xs, fontWeight: typography.weight.bold },
})
