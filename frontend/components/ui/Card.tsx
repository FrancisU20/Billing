import React from 'react'
import { StyleSheet, View, type ViewProps } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { shadow, radius, spacing } from '@/constants/tokens'

type CardVariant = 'default' | 'muted' | 'elevated'

interface CardProps extends ViewProps {
  children: React.ReactNode
  elevated?: boolean
  padded?: boolean
  variant?: CardVariant
}

export function Card({ children, elevated = false, padded = true, variant = 'default', style, ...props }: CardProps) {
  const { semantic } = useTheme()

  const variantBg: Record<CardVariant, string> = {
    default: semantic.bg.card,
    muted: semantic.bg.muted,
    elevated: semantic.bg.elevated,
  }

  return (
    <View
      {...props}
      style={[
        staticStyles.base,
        { backgroundColor: variantBg[variant], borderColor: semantic.border.default },
        elevated && shadow.lg,
        padded && staticStyles.padded,
        style,
      ]}
    >
      {children}
    </View>
  )
}

const staticStyles = StyleSheet.create({
  base: { borderRadius: radius.xl, borderWidth: 1 },
  padded: { padding: spacing[5] },
})
