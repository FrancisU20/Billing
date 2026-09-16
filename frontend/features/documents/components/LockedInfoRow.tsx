import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'

interface LockedInfoRowProps {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  value: string
  meta?: string
  monoMeta?: boolean
}

export function LockedInfoRow({ icon, label, value, meta, monoMeta = false }: LockedInfoRowProps) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.row,
        { backgroundColor: semantic.bg.primary, borderColor: semantic.border.default },
      ]}
    >
      <View style={styles.icon}>
        <Ionicons name={icon} size={18} color={semantic.accent.default} />
      </View>
      <View style={styles.text}>
        <Text style={[styles.label, { color: semantic.text.secondary }]}>{label}</Text>
        <Text style={[styles.value, { color: semantic.text.primary }]}>{value}</Text>
        {meta ? (
          <Text
            style={[styles.meta, monoMeta && styles.metaMono, { color: semantic.text.tertiary }]}
          >
            {meta}
          </Text>
        ) : null}
      </View>
      <Ionicons name="lock-closed-outline" size={18} color={semantic.text.tertiary} />
    </View>
  )
}

const styles = StyleSheet.create({
  row: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    minHeight: 66,
    padding: spacing[3],
  },
  icon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  text: { flex: 1, gap: spacing[1] - 2 },
  label: { fontSize: typography.size.xs, fontWeight: typography.weight.semibold },
  value: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  meta: { fontSize: typography.size.xs },
  metaMono: { fontFamily: typography.fontFamily.mono },
})
