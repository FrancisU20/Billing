import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

export function FilterBlock({ label, children }: { label: string; children: React.ReactNode }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.block}>
      <Text style={[styles.label, { color: semantic.text.secondary }]}>{label}</Text>
      {children}
    </View>
  )
}

export function FilterPill({
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
  block: { minWidth: 260, flex: 1, gap: spacing[2] },
  label: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  pill: {
    alignItems: 'center',
    borderRadius: radius.full,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 34,
    paddingHorizontal: spacing[3],
  },
  pillText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
})
