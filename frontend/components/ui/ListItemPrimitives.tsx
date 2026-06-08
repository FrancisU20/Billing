import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { radius, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'

export function ListItemMeta({
  icon,
  text,
  mono = false,
}: {
  icon: keyof typeof Ionicons.glyphMap
  text: string
  mono?: boolean
}) {
  const { semantic } = useTheme()
  return (
    <View style={styles.metaItem}>
      <Ionicons name={icon} size={13} color={semantic.text.tertiary} />
      <Text
        style={[styles.metaText, mono && styles.mono, { color: semantic.text.tertiary }]}
        numberOfLines={1}
      >
        {text}
      </Text>
    </View>
  )
}

export function ListItemAction({
  icon,
  label,
  danger = false,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  danger?: boolean
  onPress: () => void
}) {
  const { semantic } = useTheme()
  return (
    <Pressable
      accessibilityLabel={label}
      onPress={(event) => {
        event.stopPropagation()
        onPress()
      }}
      hitSlop={8}
      style={({ pressed }) => [
        styles.actionButton,
        {
          backgroundColor: pressed
            ? danger
              ? semantic.status.errorBg
              : semantic.bg.tertiary
            : semantic.bg.primary,
          borderColor: semantic.border.default,
        },
      ]}
    >
      <Ionicons
        name={icon}
        size={17}
        color={danger ? semantic.status.error : semantic.text.secondary}
      />
    </Pressable>
  )
}

const styles = StyleSheet.create({
  metaItem: { alignItems: 'center', flexDirection: 'row', gap: spacing[1], maxWidth: 220 },
  metaText: { fontSize: typography.size.xs },
  mono: { fontFamily: typography.fontFamily.mono },
  actionButton: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
})
