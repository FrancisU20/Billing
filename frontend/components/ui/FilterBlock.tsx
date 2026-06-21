import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'

export function FilterBlock({ label, children }: { label: string; children: React.ReactNode }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.block}>
      <Text style={[styles.label, { color: semantic.text.secondary }]}>{label}</Text>
      {children}
    </View>
  )
}

const styles = StyleSheet.create({
  block: { minWidth: 260, flex: 1, gap: spacing[2] },
  label: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
})
