import React from 'react'
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing } from '@/constants/tokens'

interface LoadingSpinnerProps {
  label?: string
  size?: 'small' | 'large'
  fullScreen?: boolean
}

export function LoadingSpinner({ label, size = 'large', fullScreen = false }: LoadingSpinnerProps) {
  const { semantic } = useTheme()

  return (
    <View style={[staticStyles.container, fullScreen && { flex: 1, backgroundColor: semantic.bg.primary }]}>
      <ActivityIndicator size={size} color={semantic.accent.default} />
      {label ? <Text style={[staticStyles.label, { color: semantic.text.secondary }]}>{label}</Text> : null}
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
  label: { fontSize: typography.size.sm },
})
