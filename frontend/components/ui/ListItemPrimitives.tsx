import React from 'react'
import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
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

/**
 * Columna "label arriba, valor abajo" para las filas de listado en su variante desktop
 * (ver ClientListItem/TenantListItem/PlanListItem/ProductListItem/DocumentListItem). El
 * ancho de columna (flexBasis/flex/minWidth) varia por dominio y se pasa via `style`.
 */
export function ListCell({
  label,
  value,
  mono = false,
  style,
}: {
  label: string
  value: string
  mono?: boolean
  style?: StyleProp<ViewStyle>
}) {
  const { semantic } = useTheme()
  return (
    <View style={[styles.cell, style]}>
      <Text style={[styles.cellLabel, { color: semantic.text.tertiary }]}>{label}</Text>
      <Text
        style={[styles.cellValue, mono && styles.mono, { color: semantic.text.primary }]}
        numberOfLines={1}
      >
        {value}
      </Text>
    </View>
  )
}

/**
 * Avatar circular de las filas de listado: iniciales (Client/Tenant) o un icono fijo
 * (Plan). Pasar exactamente una de las dos props de contenido.
 */
export function EntityAvatar({
  initials,
  icon,
  size = 'sm',
}: {
  initials?: string
  icon?: keyof typeof Ionicons.glyphMap
  size?: 'sm' | 'md'
}) {
  const { semantic } = useTheme()
  const dimension = size === 'md' ? sizes.avatarMd : sizes.avatarSm
  return (
    <View
      style={[
        styles.avatar,
        { width: dimension, height: dimension, backgroundColor: semantic.accent.subtle },
      ]}
    >
      {icon ? (
        <Ionicons name={icon} size={20} color={semantic.accent.default} />
      ) : (
        <Text style={[styles.avatarText, { color: semantic.accent.default }]}>{initials}</Text>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  avatar: { alignItems: 'center', borderRadius: radius.md, justifyContent: 'center' },
  avatarText: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
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
  cell: { gap: spacing[1] },
  cellLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  cellValue: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
})
