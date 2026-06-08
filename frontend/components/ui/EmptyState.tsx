import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing } from '@/constants/tokens'
import { Button } from './Button'

interface EmptyStateProps {
  icon?: keyof typeof Ionicons.glyphMap
  title: string
  description?: string
  action?: { label: string; onPress: () => void }
}

export function EmptyState({ icon = 'file-tray-outline', title, description, action }: EmptyStateProps) {
  const { semantic } = useTheme()

  return (
    <View style={staticStyles.container}>
      <View style={[staticStyles.iconWrap, { backgroundColor: semantic.bg.tertiary }]}>
        <Ionicons name={icon} size={40} color={semantic.text.tertiary} />
      </View>
      <Text style={[staticStyles.title, { color: semantic.text.primary }]}>{title}</Text>
      {description ? <Text style={[staticStyles.description, { color: semantic.text.secondary }]}>{description}</Text> : null}
      {action ? (
        <Button variant="outline" size="sm" onPress={action.onPress} style={{ marginTop: spacing[2] } as any}>
          {action.label}
        </Button>
      ) : null}
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center', padding: spacing[10], gap: spacing[3] },
  iconWrap: { width: 72, height: 72, borderRadius: 36, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.semibold, textAlign: 'center' },
  description: { fontSize: typography.size.sm, textAlign: 'center', lineHeight: typography.size.sm * 1.6 },
})
