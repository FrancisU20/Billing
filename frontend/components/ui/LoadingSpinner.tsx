import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing } from '@/constants/tokens'
import { LoadingLogo, LoadingScreen } from '@/components/branding/LoadingScreen'

interface LoadingSpinnerProps {
  label?: string
  size?: 'small' | 'large'
  fullScreen?: boolean
  compact?: boolean
}

export function LoadingSpinner({
  label,
  size = 'large',
  fullScreen = false,
  compact = false,
}: LoadingSpinnerProps) {
  const { semantic } = useTheme()
  const logoSize = size === 'small' ? 40 : 64

  if (fullScreen) return <LoadingScreen label={label} />

  return (
    <View style={[staticStyles.container, compact && staticStyles.compact]}>
      <LoadingLogo size={logoSize} />
      {label ? (
        <Text style={[staticStyles.label, { color: semantic.text.secondary }]}>{label}</Text>
      ) : null}
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing[3],
    padding: spacing[8],
  },
  compact: { padding: spacing[2] },
  label: { fontSize: typography.size.sm },
})
