import React from 'react'
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { overlay, typography, radius, spacing } from '@/constants/tokens'

type Variant = 'primary' | 'secondary' | 'danger' | 'warning' | 'ghost' | 'outline'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends Omit<PressableProps, 'style'> {
  children: React.ReactNode
  variant?: Variant
  size?: Size
  isLoading?: boolean
  isDisabled?: boolean
  fullWidth?: boolean
  style?: StyleProp<ViewStyle>
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  isDisabled = false,
  fullWidth = false,
  style: externalStyle,
  ...props
}: ButtonProps) {
  const { semantic } = useTheme()
  const disabled = isDisabled || isLoading

  const variantBg: Record<Variant, string> = {
    primary: semantic.accent.default,
    secondary: semantic.bg.tertiary,
    danger: semantic.status.error,
    warning: semantic.status.warning,
    ghost: 'transparent',
    outline: 'transparent',
  }
  const variantBgPressed: Record<Variant, string> = {
    primary: semantic.accent.hover,
    secondary: semantic.border.default,
    danger: semantic.status.error,
    warning: semantic.status.warning,
    ghost: semantic.bg.secondary,
    outline: semantic.bg.secondary,
  }
  const variantText: Record<Variant, string> = {
    primary: overlay.text.primary,
    secondary: semantic.text.primary,
    danger: overlay.text.primary,
    warning: overlay.text.primary,
    ghost: semantic.accent.default,
    outline: semantic.text.primary,
  }

  return (
    <Pressable
      {...props}
      disabled={disabled}
      style={({ pressed }) => [
        staticStyles.base,
        staticStyles[size],
        fullWidth && staticStyles.fullWidth,
        {
          backgroundColor: pressed && !disabled ? variantBgPressed[variant] : variantBg[variant],
          borderWidth: variant === 'outline' ? 1.5 : 0,
          borderColor: variant === 'outline' ? semantic.border.default : undefined,
          borderRadius: radius.md,
          opacity: disabled ? 0.45 : 1,
        },
        externalStyle,
      ]}
    >
      {isLoading ? (
        <ActivityIndicator
          size="small"
          color={
            variant === 'primary' || variant === 'danger' || variant === 'warning'
              ? overlay.text.primary
              : semantic.accent.default
          }
          style={{ marginRight: spacing[2] }}
        />
      ) : null}
      <Text
        style={[
          staticStyles.label,
          staticStyles[`${size}Label` as keyof typeof staticStyles],
          { color: variantText[variant] },
        ]}
      >
        {children}
      </Text>
    </Pressable>
  )
}

const staticStyles = StyleSheet.create({
  base: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
  fullWidth: { width: '100%' },
  sm: { paddingHorizontal: spacing[3], paddingVertical: spacing[2] - 2, gap: spacing[1] },
  md: { paddingHorizontal: spacing[4], paddingVertical: spacing[3] - 2, gap: spacing[2] },
  lg: { paddingHorizontal: spacing[6], paddingVertical: spacing[4] - 4, gap: spacing[2] },
  label: { fontWeight: typography.weight.semibold, includeFontPadding: false },
  smLabel: { fontSize: typography.size.sm },
  mdLabel: { fontSize: typography.size.base },
  lgLabel: { fontSize: typography.size.md },
})
