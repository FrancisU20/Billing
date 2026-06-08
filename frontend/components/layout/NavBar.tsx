import React from 'react'
import { Pressable, StyleSheet, Text, View, type PressableProps } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing, radius } from '@/constants/tokens'

interface NavBarProps {
  title: string
  subtitle?: string
  canGoBack?: boolean
  leftContent?: React.ReactNode
  rightContent?: React.ReactNode
}

interface NavIconButtonProps extends PressableProps {
  icon: keyof typeof Ionicons.glyphMap
}

export function NavBar({ title, subtitle, canGoBack, leftContent, rightContent }: NavBarProps) {
  const router = useRouter()
  const { semantic } = useTheme()

  const resolvedLeft =
    leftContent ?? (canGoBack ? <NavIconButton icon="chevron-back" onPress={router.back} /> : null)

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.page, borderBottomColor: semantic.border.default },
      ]}
    >
      <View style={styles.content}>
        {resolvedLeft}

        <View style={styles.heading}>
          <Text style={[styles.title, { color: semantic.text.primary }]} numberOfLines={1}>
            {title}
          </Text>
          {subtitle ? (
            <Text style={[styles.subtitle, { color: semantic.text.secondary }]} numberOfLines={1}>
              {subtitle}
            </Text>
          ) : null}
        </View>

        {rightContent}
      </View>
    </View>
  )
}

export function NavIconButton({ icon, style, ...props }: NavIconButtonProps) {
  const { semantic } = useTheme()

  return (
    <Pressable
      {...props}
      style={(state) => [
        styles.iconBtn,
        {
          backgroundColor: state.pressed ? semantic.bg.muted : semantic.bg.elevated,
          borderColor: semantic.border.default,
        },
        typeof style === 'function' ? style(state) : style,
      ]}
      hitSlop={8}
    >
      <Ionicons name={icon} size={20} color={semantic.text.primary} />
    </Pressable>
  )
}

const styles = StyleSheet.create({
  container: { borderBottomWidth: 1, paddingHorizontal: spacing[5], paddingVertical: spacing[3] },
  content: { minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  heading: { flex: 1, minWidth: 0, gap: 2 },
  title: { fontSize: typography.size.md, fontWeight: typography.weight.semibold },
  subtitle: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
  iconBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.full,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
})
