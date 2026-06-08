import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, radius, spacing } from '@/constants/tokens'
import type { ApiError } from '@/lib/api/errors'

export function ApiErrorBanner({ error }: { error: ApiError }) {
  const { semantic } = useTheme()

  return (
    <View
      style={[
        staticStyles.container,
        {
          backgroundColor: semantic.status.errorBg,
          borderLeftColor: semantic.status.error,
        },
      ]}
    >
      <Ionicons name="alert-circle" size={16} color={semantic.status.error} />
      <Text style={[staticStyles.message, { color: semantic.status.error }]}>{error.message}</Text>
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing[2],
    borderRadius: radius.md,
    padding: spacing[3],
    borderLeftWidth: 3,
  },
  message: { flex: 1, fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.5 },
})
