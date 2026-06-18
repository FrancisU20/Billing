import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { BUYER_ID_TYPE_OPTIONS } from '../constants'
import type { BuyerIdType } from '../types'

interface BuyerIdTypePickerProps {
  value: BuyerIdType
  onChange: (value: BuyerIdType) => void
}

export function BuyerIdTypePicker({ value, onChange }: BuyerIdTypePickerProps) {
  return (
    <View style={styles.grid}>
      {BUYER_ID_TYPE_OPTIONS.map((option) => (
        <OptionTile
          key={option.value}
          icon={option.icon}
          label={option.label}
          selected={value === option.value}
          onPress={() => onChange(option.value)}
        />
      ))}
    </View>
  )
}

function OptionTile({
  icon,
  label,
  selected,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  selected: boolean
  onPress: () => void
}) {
  const { semantic } = useTheme()
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.optionTile,
        {
          backgroundColor: selected
            ? semantic.accent.subtle
            : pressed
              ? semantic.bg.secondary
              : semantic.bg.primary,
          borderColor: selected ? semantic.accent.default : semantic.border.default,
        },
      ]}
    >
      <Ionicons
        name={icon}
        size={18}
        color={selected ? semantic.accent.default : semantic.text.secondary}
      />
      <Text
        style={[
          styles.optionLabel,
          { color: selected ? semantic.accent.default : semantic.text.secondary },
        ]}
        numberOfLines={1}
      >
        {label}
      </Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  optionTile: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[2],
    minHeight: 42,
    minWidth: 132,
    paddingHorizontal: spacing[3],
  },
  optionLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
})
