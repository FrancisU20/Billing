import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

interface SegmentedOption<T extends string> {
  value: T
  label: string
}

interface SegmentedControlProps<T extends string> {
  options: ReadonlyArray<SegmentedOption<T>>
  value: T
  onChange: (value: T) => void
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  const { semantic } = useTheme()

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.tertiary }]}>
      {options.map((option) => {
        const selected = option.value === value
        return (
          <Pressable
            key={option.value}
            onPress={() => onChange(option.value)}
            style={({ pressed }) => [
              styles.option,
              {
                backgroundColor: selected
                  ? semantic.bg.elevated
                  : pressed
                    ? semantic.bg.secondary
                    : 'transparent',
                borderColor: selected ? semantic.border.default : 'transparent',
              },
            ]}
          >
            <Text
              style={[
                styles.label,
                { color: selected ? semantic.text.primary : semantic.text.secondary },
              ]}
              numberOfLines={1}
            >
              {option.label}
            </Text>
          </Pressable>
        )
      })}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignSelf: 'flex-start',
    borderRadius: radius.md,
    flexDirection: 'row',
    gap: spacing[1],
    padding: spacing[1],
  },
  option: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 34,
    minWidth: 88,
    paddingHorizontal: spacing[3],
  },
  label: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    includeFontPadding: false,
  },
})
