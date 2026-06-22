import React from 'react'
import { StyleSheet, Text, View, type TextInputProps } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { overlay, typography, spacing } from '@/constants/tokens'
import { Input } from './Input'

export interface FormFieldProps extends TextInputProps {
  label: string
  error?: string
  hint?: string
  required?: boolean
  isDisabled?: boolean
  leftIcon?: keyof typeof Ionicons.glyphMap
  rightElement?: React.ReactNode
  dark?: boolean
}

export function FormField({
  label,
  error,
  hint,
  required,
  isDisabled,
  leftIcon,
  rightElement,
  dark,
  ...inputProps
}: FormFieldProps) {
  const { semantic } = useTheme()

  const labelColor = dark ? overlay.text.label : semantic.text.primary
  const hintColor = dark ? overlay.text.faint : semantic.text.secondary

  return (
    <View style={staticStyles.container}>
      <View style={staticStyles.labelRow}>
        <Text style={[staticStyles.label, { color: labelColor }]}>{label}</Text>
        {required ? (
          <Text style={{ color: semantic.status.error, fontSize: typography.size.sm }}> *</Text>
        ) : null}
      </View>

      <Input
        {...inputProps}
        hasError={!!error}
        isDisabled={isDisabled}
        leftIcon={leftIcon}
        rightElement={rightElement}
        dark={dark}
        accessibilityLabel={label}
      />

      {error ? (
        <View style={staticStyles.feedbackRow}>
          <Ionicons name="alert-circle-outline" size={13} color={semantic.status.error} />
          <Text style={[staticStyles.feedbackText, { color: semantic.status.error }]}>{error}</Text>
        </View>
      ) : hint ? (
        <Text style={[staticStyles.feedbackText, { color: hintColor }]}>{hint}</Text>
      ) : null}
    </View>
  )
}

const staticStyles = StyleSheet.create({
  container: { gap: spacing[1] + 2 },
  labelRow: { flexDirection: 'row', alignItems: 'center' },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  feedbackRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[1] },
  feedbackText: { fontSize: typography.size.xs },
})
