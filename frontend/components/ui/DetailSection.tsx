import React from 'react'
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

interface DetailSectionProps {
  title: string
  icon: keyof typeof Ionicons.glyphMap
  children: React.ReactNode
  /** `grid` (default) wraps fields in a responsive row; `stack` lays children out as a column. */
  layout?: 'grid' | 'stack'
  style?: StyleProp<ViewStyle>
  contentStyle?: StyleProp<ViewStyle>
}

export function DetailSection({
  title,
  icon,
  children,
  layout = 'grid',
  style,
  contentStyle,
}: DetailSectionProps) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.section,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
        style,
      ]}
    >
      <View style={styles.sectionTitleRow}>
        <Ionicons name={icon} size={17} color={semantic.accent.default} />
        <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>{title}</Text>
      </View>
      <View style={[layout === 'grid' ? styles.fieldGrid : styles.stack, contentStyle]}>
        {children}
      </View>
    </View>
  )
}

interface DetailFieldProps {
  label: string
  value: string
  mono?: boolean
}

export function DetailField({ label, value, mono = false }: DetailFieldProps) {
  const { semantic } = useTheme()
  return (
    <View style={styles.field}>
      <Text style={[styles.fieldLabel, { color: semantic.text.secondary }]}>{label}</Text>
      <Text
        style={[styles.fieldValue, mono && styles.mono, { color: semantic.text.primary }]}
        numberOfLines={2}
      >
        {value}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  section: { borderRadius: radius.md, borderWidth: 1, gap: spacing[4], padding: spacing[5] },
  sectionTitleRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  sectionTitle: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  fieldGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[4] },
  stack: { gap: spacing[4] },
  field: { flex: 1, minWidth: 220, gap: spacing[1] },
  fieldLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  fieldValue: { fontSize: typography.size.base },
  mono: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.sm },
})
