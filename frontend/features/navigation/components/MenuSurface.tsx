import React from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, spacing, radius } from '@/constants/tokens'

type PanelSide = 'left' | 'right'

interface MenuSurfaceProps {
  visible: boolean
  onClose: () => void
  side: PanelSide
  children: React.ReactNode
}

interface MenuItemProps {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  active?: boolean
  danger?: boolean
  disabled?: boolean
  onPress: () => void
}

export function MenuSurface({ visible, onClose, side, children }: MenuSurfaceProps) {
  const { semantic } = useTheme()

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <Pressable style={styles.modalBackdrop} onPress={onClose} />
        <View
          style={[
            styles.menuPanel,
            side === 'left' ? styles.leftPanel : styles.rightPanel,
            { backgroundColor: semantic.bg.primary, borderColor: semantic.border.default },
          ]}
        >
          {children}
        </View>
      </View>
    </Modal>
  )
}

export function MenuEyebrow({ label }: { label: string }) {
  const { semantic } = useTheme()
  return <Text style={[styles.menuEyebrow, { color: semantic.text.secondary }]}>{label}</Text>
}

export function MenuDivider() {
  const { semantic } = useTheme()
  return <View style={[styles.menuDivider, { backgroundColor: semantic.border.default }]} />
}

export function MenuItem({
  icon,
  label,
  active = false,
  danger = false,
  disabled = false,
  onPress,
}: MenuItemProps) {
  const { semantic } = useTheme()
  const color = danger
    ? semantic.status.error
    : active
      ? semantic.accent.default
      : semantic.text.primary
  const iconColor = danger
    ? semantic.status.error
    : active
      ? semantic.accent.default
      : semantic.text.secondary

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.menuItem,
        {
          backgroundColor: active || pressed ? semantic.accent.subtle : semantic.bg.primary,
          opacity: disabled ? 0.55 : 1,
        },
      ]}
    >
      <Ionicons name={icon} size={18} color={iconColor} />
      <Text style={[styles.menuItemText, { color }]}>{label}</Text>
    </Pressable>
  )
}

export const menuLayoutStyles = StyleSheet.create({
  menuItems: { gap: spacing[1] },
  accountHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    padding: spacing[2],
  },
  accountCopy: { flex: 1, minWidth: 0, gap: spacing[1] },
  accountEmail: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  accountRole: { fontSize: typography.size.xs, fontWeight: typography.weight.medium },
})

const styles = StyleSheet.create({
  modalOverlay: { flex: 1 },
  modalBackdrop: { position: 'absolute', left: 0, right: 0, top: 0, bottom: 0 },
  menuPanel: {
    position: 'absolute',
    top: spacing[20],
    minWidth: 240,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing[3],
  },
  leftPanel: { left: spacing[5] },
  rightPanel: { right: spacing[5], width: 300 },
  menuEyebrow: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[2],
  },
  menuDivider: { height: 1, marginVertical: spacing[2] },
  menuItem: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    borderRadius: radius.md,
    paddingHorizontal: spacing[3],
  },
  menuItemText: { flex: 1, fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
})
