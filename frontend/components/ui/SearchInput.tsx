import React from 'react'
import { Pressable, StyleSheet, Text, View, type TextInputProps } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Input } from '@/components/ui/Input'
import { spacing, typography } from '@/constants/tokens'
import { useDebouncedSearch } from '@/lib/hooks/useDebouncedSearch'
import { useTheme } from '@/lib/theme-context'

interface SearchInputProps extends Omit<TextInputProps, 'value' | 'onChangeText'> {
  value: string
  onChangeText: (value: string) => void
  onSearchChange: (query: string) => void
  leftIcon?: keyof typeof Ionicons.glyphMap
  minLength?: number
  debounceMs?: number
  helperText?: string
}

export function SearchInput({
  value,
  onChangeText,
  onSearchChange,
  minLength = 3,
  debounceMs = 400,
  helperText,
  leftIcon = 'search-outline',
  ...props
}: SearchInputProps) {
  const { semantic } = useTheme()
  const { shouldWaitForMoreCharacters } = useDebouncedSearch(value, onSearchChange, {
    minLength,
    debounceMs,
  })
  const hint =
    helperText ??
    (shouldWaitForMoreCharacters
      ? `Escribe al menos ${minLength} caracteres para buscar.`
      : undefined)

  function clear() {
    onChangeText('')
  }

  return (
    <View style={styles.container}>
      <Input
        {...props}
        leftIcon={leftIcon}
        value={value}
        onChangeText={onChangeText}
        rightElement={
          value ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Limpiar búsqueda"
              hitSlop={8}
              onPress={clear}
            >
              <Ionicons name="close-circle-outline" size={19} color={semantic.text.tertiary} />
            </Pressable>
          ) : null
        }
      />
      {hint ? <Text style={[styles.hint, { color: semantic.text.tertiary }]}>{hint}</Text> : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[1] },
  hint: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.4 },
})
