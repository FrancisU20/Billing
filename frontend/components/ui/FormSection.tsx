import React from 'react'
import { StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'

interface FormSectionProps {
  title: string
  icon: keyof typeof Ionicons.glyphMap
  children: React.ReactNode
  fill?: boolean
  style?: StyleProp<ViewStyle>
  contentStyle?: StyleProp<ViewStyle>
}

export function FormSection({
  title,
  icon,
  children,
  fill = false,
  style,
  contentStyle,
}: FormSectionProps) {
  const { semantic } = useTheme()
  return (
    <View
      style={[
        styles.section,
        fill && styles.fill,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
        style,
      ]}
    >
      <View style={styles.header}>
        <View style={[styles.icon, { backgroundColor: semantic.accent.subtle }]}>
          <Ionicons name={icon} size={17} color={semantic.accent.default} />
        </View>
        <Text style={[styles.title, { color: semantic.text.primary }]}>{title}</Text>
      </View>
      <View style={[styles.body, contentStyle]}>{children}</View>
    </View>
  )
}

const styles = StyleSheet.create({
  section: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[4],
  },
  fill: { flex: 1 },
  header: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  icon: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.icon,
    justifyContent: 'center',
    width: sizes.icon,
  },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.bold },
  body: { gap: spacing[4] },
})
