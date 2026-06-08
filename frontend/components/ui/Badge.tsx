import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { typography, radius, spacing } from '@/constants/tokens'

type BadgeVariant = 'success' | 'warning' | 'error' | 'neutral' | 'primary'

interface BadgeProps {
  label: string
  variant?: BadgeVariant
  size?: 'sm' | 'md'
}

export function Badge({ label, variant = 'neutral', size = 'md' }: BadgeProps) {
  const { semantic } = useTheme()

  const variantMap: Record<BadgeVariant, { bg: string; text: string }> = {
    success: { bg: semantic.status.successBg, text: semantic.status.success },
    warning: { bg: semantic.status.warningBg, text: semantic.status.warning },
    error: { bg: semantic.status.errorBg, text: semantic.status.error },
    neutral: { bg: semantic.bg.tertiary, text: semantic.text.secondary },
    primary: { bg: semantic.accent.subtle, text: semantic.accent.default },
  }

  const { bg, text } = variantMap[variant]

  return (
    <View style={[staticStyles.base, size === 'sm' && staticStyles.sm, { backgroundColor: bg }]}>
      <Text style={[staticStyles.label, size === 'sm' && staticStyles.smLabel, { color: text }]}>
        {label}
      </Text>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  base: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing[2] + 2,
    paddingVertical: spacing[1] - 1,
    borderRadius: radius.full,
  },
  sm: { paddingHorizontal: spacing[2], paddingVertical: 2 },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  smLabel: { fontSize: typography.size.xs },
})
