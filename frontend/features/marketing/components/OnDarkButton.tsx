import React from 'react'
import { Pressable, StyleSheet, Text, type PressableProps } from 'react-native'
import { overlay, radius, spacing, typography } from '@/constants/tokens'

interface OnDarkButtonProps extends Omit<PressableProps, 'style'> {
  children: React.ReactNode
  size?: 'sm' | 'lg'
}

/**
 * Boton outline para usarse sobre superficies siempre oscuras (header/hero/CTA
 * de la landing), donde los tokens semanticos de Button no garantizan
 * contraste en tema claro.
 */
export function OnDarkButton({ children, size = 'lg', ...props }: OnDarkButtonProps) {
  return (
    <Pressable
      {...props}
      style={({ pressed }) => [
        styles.base,
        styles[size],
        { borderWidth: 1.5, borderColor: overlay.border.strong },
        pressed && { opacity: 0.85 },
      ]}
    >
      <Text style={[styles.label, styles[`${size}Label`]]}>{children}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.md,
  },
  sm: { paddingHorizontal: spacing[4], paddingVertical: spacing[2] },
  lg: { paddingHorizontal: spacing[6], paddingVertical: spacing[3] + 2 },
  label: { color: overlay.text.primary, fontWeight: typography.weight.semibold },
  smLabel: { fontSize: typography.size.sm },
  lgLabel: { fontSize: typography.size.md },
})
