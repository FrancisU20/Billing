import React, { forwardRef, useState } from 'react'
import {
  Platform,
  Pressable,
  StyleSheet,
  TextInput,
  View,
  type TextInputProps,
  type TextStyle,
  type ViewStyle,
} from 'react-native'
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

type WebTextInputStyle = Omit<TextStyle, 'outlineColor' | 'outlineStyle' | 'outlineWidth'> & {
  outlineColor?: string
  outlineStyle?: 'solid'
  outlineWidth?: number
}

const webTextInputReset: WebTextInputStyle = {
  outlineColor: 'transparent',
  outlineStyle: 'solid',
  outlineWidth: 0,
  // iOS Safari hace autozoom al enfocar un input con font-size < 16px.
  ...(Platform.OS === 'web' ? { fontSize: typography.size.md } : null),
}

// Cursor "no permitido" en vez del cursor de texto (I) — `editable={false}` ya bloquea
// la edicion, pero sin esto el cursor del mouse sigue pareciendo el de un campo
// editable, lo cual confunde (ver feedback: "que no cambie el cursor a I"). El tipo
// `CursorValue` de RN solo declara 'auto'/'pointer' — react-native-web si soporta el
// resto del enum CSS en runtime, de ahi el cast en cada sitio de uso.
function disabledCursorStyle(isDisabled?: boolean): { cursor: 'not-allowed' } | null {
  if (!isDisabled || Platform.OS !== 'web') return null
  return { cursor: 'not-allowed' }
}

export const Input = forwardRef<TextInput, InputProps>(
  (
    { hasError, isDisabled, leftIcon, rightElement, secureTextEntry, dark, style, value, ...props },
    ref,
  ) => {
    const { semantic } = useTheme()
    const [focused, setFocused] = useState(false)
    const [visible, setVisible] = useState(false)

    const borderColor = hasError
      ? semantic.status.error
      : focused
        ? semantic.border.focus
        : dark
          ? overlay.border.hover
          : semantic.border.default

    const bg = dark
      ? focused
        ? overlay.surface.hover
        : overlay.surface.default
      : hasError
        ? semantic.status.errorBg
        : semantic.bg.primary

    const iconColor = hasError
      ? semantic.status.error
      : focused
        ? semantic.accent.default
        : dark
          ? overlay.text.icon
          : semantic.text.tertiary

    return (
      <View
        style={[
          staticStyles.container,
          { borderColor, backgroundColor: bg, opacity: isDisabled ? 0.5 : 1 },
          disabledCursorStyle(isDisabled) as unknown as ViewStyle,
        ]}
      >
        {leftIcon ? (
          <Ionicons name={leftIcon} size={18} color={iconColor} style={staticStyles.leftIcon} />
        ) : null}

        <TextInput
          ref={ref}
          {...props}
          value={value ?? ''}
          editable={!isDisabled}
          // En web, `editable={false}` solo bloquea la escritura: el input sigue siendo
          // foco-able al click y muestra el caret titilando, como si se pudiera editar.
          // `pointerEvents="none"` evita que el click llegue al input.
          pointerEvents={isDisabled ? 'none' : undefined}
          secureTextEntry={secureTextEntry && !visible}
          onFocus={(e) => {
            if (isDisabled) return
            setFocused(true)
            props.onFocus?.(e)
          }}
          onBlur={(e) => {
            setFocused(false)
            props.onBlur?.(e)
          }}
          style={[
            staticStyles.input,
            webTextInputReset,
            { color: dark ? overlay.text.primary : semantic.text.primary },
            disabledCursorStyle(isDisabled) as unknown as TextStyle,
            style,
          ]}
          placeholderTextColor={dark ? overlay.text.placeholder : semantic.text.tertiary}
          selectionColor={semantic.accent.default}
        />

        {secureTextEntry ? (
          <Pressable onPress={() => setVisible((v) => !v)} style={staticStyles.rightEl}>
            <Ionicons
              name={visible ? 'eye-outline' : 'eye-off-outline'}
              size={18}
              color={iconColor}
            />
          </Pressable>
        ) : rightElement ? (
          <View style={staticStyles.rightEl}>{rightElement}</View>
        ) : isDisabled ? (
          <View style={staticStyles.rightEl}>
            <Ionicons name="lock-closed-outline" size={16} color={iconColor} />
          </View>
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
  },
  rightEl: { marginLeft: spacing[2] },
})
