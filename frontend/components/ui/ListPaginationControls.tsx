import React, { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
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
  /** Cuando se provee, habilita "Ir a página" — solo disponible para listados que ya
   * tienen el set completo en memoria (`useEagerPagedList`/`useLocalPagedItems`). */
  onGoToPage?: (page: number) => void
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
  onGoToPage,
}: ListPaginationControlsProps) {
  const { semantic } = useTheme()
  const hasTotal = totalItems != null && totalPages != null
  const canJump = Boolean(onGoToPage) && hasTotal && (totalPages ?? 0) > 2

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
        {canJump ? (
          <PageJumpControl page={page} totalPages={totalPages as number} onGoToPage={onGoToPage!} />
        ) : null}
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

function PageJumpControl({
  page,
  totalPages,
  onGoToPage,
}: {
  page: number
  totalPages: number
  onGoToPage: (page: number) => void
}) {
  const { semantic } = useTheme()
  const [draft, setDraft] = useState('')

  function submit() {
    const target = Number(draft)
    if (Number.isFinite(target) && target >= 1) {
      onGoToPage(target)
    }
    setDraft('')
  }

  return (
    <View style={styles.jumpGroup}>
      <Text style={[styles.pageSizeLabel, { color: semantic.text.secondary }]}>Ir a página</Text>
      <View style={styles.jumpInput}>
        <Input
          value={draft}
          onChangeText={setDraft}
          placeholder={String(page)}
          keyboardType="number-pad"
          onSubmitEditing={submit}
        />
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Ir a la página (1-${totalPages})`}
        hitSlop={8}
        onPress={submit}
        style={({ pressed }) => [
          styles.jumpButton,
          {
            backgroundColor: pressed ? semantic.bg.secondary : semantic.bg.primary,
            borderColor: semantic.border.default,
          },
        ]}
      >
        <Ionicons name="arrow-forward-outline" size={16} color={semantic.accent.default} />
      </Pressable>
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
  jumpGroup: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  jumpInput: { width: 64 },
  jumpButton: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
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
