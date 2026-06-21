import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { radius, sizes, spacing, typography } from '@/constants/tokens'

interface DetailHeaderProps {
  title: string
  subtitle?: string
  eyebrow?: string
  icon?: keyof typeof Ionicons.glyphMap
  initials?: string
  badges?: React.ReactNode
  actions?: React.ReactNode
}

export function DetailHeader({
  title,
  subtitle,
  eyebrow,
  icon,
  initials,
  badges,
  actions,
}: DetailHeaderProps) {
  const { semantic } = useTheme()

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <View style={[styles.avatar, { backgroundColor: semantic.accent.subtle }]}>
        {icon ? (
          <Ionicons name={icon} size={24} color={semantic.accent.default} />
        ) : (
          <Text style={[styles.avatarText, { color: semantic.accent.default }]}>{initials}</Text>
        )}
      </View>

      <View style={styles.copy}>
        {eyebrow ? (
          <Text style={[styles.eyebrow, { color: semantic.text.tertiary }]}>{eyebrow}</Text>
        ) : null}
        <Text style={[styles.title, { color: semantic.text.primary }]}>{title}</Text>
        {subtitle ? (
          <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>{subtitle}</Text>
        ) : null}
        {badges ? <View style={styles.badgeRow}>{badges}</View> : null}
      </View>

      {actions ? <View style={styles.actions}>{actions}</View> : null}
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
    gap: spacing[4],
    padding: spacing[5],
  },
  avatar: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.avatarLg,
    justifyContent: 'center',
    width: sizes.avatarLg,
  },
  avatarText: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  copy: { flex: 1, gap: spacing[1], minWidth: 220 },
  eyebrow: { fontSize: typography.size.xs, fontWeight: typography.weight.bold },
  title: { fontSize: typography.size.xl, fontWeight: typography.weight.bold },
  subtitle: { fontSize: typography.size.sm },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2], marginTop: spacing[1] },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
})
