import React from 'react'
import { Pressable, StyleSheet } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { radius, spacing } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'

interface GenerateSkuButtonProps {
  onPress: () => void
}

export function GenerateSkuButton({ onPress }: GenerateSkuButtonProps) {
  const { semantic } = useTheme()

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Autogenerar SKU UUID"
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: pressed ? semantic.accent.muted : semantic.accent.subtle,
          borderColor: semantic.accent.muted,
        },
      ]}
    >
      <Ionicons name="sparkles-outline" size={18} color={semantic.accent.default} />
    </Pressable>
  )
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    height: 36,
    justifyContent: 'center',
    width: 36,
    marginLeft: spacing[1],
  },
})
