import React, { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

export interface FilterBarChip {
  key: string
  label: string
  onRemove: () => void
}

interface FilterBarProps {
  chips: FilterBarChip[]
  activeSecondaryCount: number
  onApply: () => void
  onReset: () => void
  children: React.ReactNode
  secondaryContent: React.ReactNode
}

/**
 * Filtros principales siempre visibles (children) + filtros secundarios colapsados
 * detrás de "Más filtros", con chips de los filtros secundarios activos para que el
 * usuario no necesite expandir el panel para saber qué está filtrando. "Limpiar" y
 * "Aplicar" viven juntos al pie del panel expandido (no hay accion de reset suelta en
 * una esquina) para que las dos acciones del panel se vean y se usen como un par.
 */
export function FilterBar({
  chips,
  activeSecondaryCount,
  onApply,
  onReset,
  children,
  secondaryContent,
}: FilterBarProps) {
  const { semantic } = useTheme()
  const [expanded, setExpanded] = useState(false)

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.titleRow}>
        <Ionicons name="filter-outline" size={18} color={semantic.accent.default} />
        <Text style={[styles.title, { color: semantic.text.primary }]}>Filtros</Text>
      </View>

      {children}

      {chips.length > 0 ? (
        <View style={styles.chipsRow}>
          {chips.map((chip) => (
            <Pressable
              key={chip.key}
              onPress={chip.onRemove}
              accessibilityRole="button"
              accessibilityLabel={`Quitar filtro ${chip.label}`}
              style={[
                styles.chip,
                { backgroundColor: semantic.accent.subtle, borderColor: semantic.accent.default },
              ]}
            >
              <Text style={[styles.chipText, { color: semantic.accent.default }]} numberOfLines={1}>
                {chip.label}
              </Text>
              <Ionicons name="close-outline" size={14} color={semantic.accent.default} />
            </Pressable>
          ))}
        </View>
      ) : null}

      <Pressable
        onPress={() => setExpanded((current) => !current)}
        style={styles.toggle}
        accessibilityRole="button"
        accessibilityLabel={expanded ? 'Ocultar más filtros' : 'Mostrar más filtros'}
      >
        <Ionicons
          name={expanded ? 'chevron-up-outline' : 'chevron-down-outline'}
          size={16}
          color={semantic.text.secondary}
        />
        <Text style={[styles.toggleText, { color: semantic.text.secondary }]}>
          {expanded ? 'Menos filtros' : 'Más filtros'}
        </Text>
        {activeSecondaryCount > 0 ? (
          <Badge label={String(activeSecondaryCount)} variant="primary" size="sm" />
        ) : null}
      </Pressable>

      {expanded ? (
        <View style={styles.secondary}>
          {secondaryContent}
          <View style={styles.panelActions}>
            <Button variant="outline" size="md" onPress={onReset}>
              Limpiar
            </Button>
            <Button variant="primary" size="md" onPress={onApply}>
              Aplicar
            </Button>
          </View>
        </View>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[4] },
  titleRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  chipsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  chip: {
    alignItems: 'center',
    borderRadius: radius.full,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[1],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
  },
  chipText: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold, maxWidth: 220 },
  toggle: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: spacing[2] },
  toggleText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  secondary: { gap: spacing[4] },
  panelActions: { flexDirection: 'row', gap: spacing[2], justifyContent: 'flex-end' },
})
