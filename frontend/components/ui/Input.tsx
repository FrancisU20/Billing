import React, { forwardRef, useState } from 'react'
import { Pressable, StyleSheet, TextInput, View, type TextInputProps } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { overlay, typography, radius, spacing } from '@/constants/tokens'

interface InputProps extends TextInputProps {
  hasError?: boolean
  isDisabled?: boolean
  leftIcon?: keyof typeof Ionicons.glyphMap
  rightElement?: React.ReactNode
  dark?: boolean
}

export const Input = forwardRef<TextInput, InputProps>(
  ({ hasError, isDisabled, leftIcon, rightElement, secureTextEntry, dark, style, value, ...props }, ref) => {
    const { semantic } = useTheme()
    const [focused, setFocused] = useState(false)
    const [visible, setVisible] = useState(false)

    const borderColor = hasError
      ? semantic.status.error
      : focused
        ? semantic.border.focus
        : dark ? overlay.border.hover : semantic.border.default

    const bg = dark
      ? focused ? overlay.surface.hover : overlay.surface.default
      : hasError ? semantic.status.errorBg : semantic.bg.primary

    const iconColor = hasError
      ? semantic.status.error
      : focused
        ? semantic.accent.default
        : dark ? overlay.text.icon : semantic.text.tertiary

    return (
      <View style={[staticStyles.container, { borderColor, backgroundColor: bg, opacity: isDisabled ? 0.5 : 1 }]}>
        {leftIcon ? (
          <Ionicons name={leftIcon} size={18} color={iconColor} style={staticStyles.leftIcon} />
        ) : null}

        <TextInput
          ref={ref}
          {...props}
          value={value ?? ''}
          editable={!isDisabled}
          secureTextEntry={secureTextEntry && !visible}
          onFocus={(e) => { setFocused(true); props.onFocus?.(e) }}
          onBlur={(e) => { setFocused(false); props.onBlur?.(e) }}
          style={[staticStyles.input, { color: dark ? overlay.text.primary : semantic.text.primary }, style]}
          placeholderTextColor={dark ? overlay.text.placeholder : semantic.text.tertiary}
          selectionColor={semantic.accent.default}
        />

        {secureTextEntry ? (
          <Pressable onPress={() => setVisible((v) => !v)} style={staticStyles.rightEl}>
            <Ionicons name={visible ? 'eye-outline' : 'eye-off-outline'} size={18} color={iconColor} />
          </Pressable>
        ) : rightElement ? (
          <View style={staticStyles.rightEl}>{rightElement}</View>
        ) : null}
      </View>
    )
  },
)

Input.displayName = 'Input'

const staticStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing[4],
    minHeight: 52,
  },
  leftIcon: { marginRight: spacing[3] },
  input: {
    flex: 1,
    fontSize: typography.size.base,
    paddingVertical: spacing[3],
    includeFontPadding: false,
    outlineWidth: 0,
    outlineStyle: 'none',
  } as any,
  rightEl: { marginLeft: spacing[2] },
})
