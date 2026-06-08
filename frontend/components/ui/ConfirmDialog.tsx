import React from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { useTheme } from '@/lib/theme-context'
import { overlay, radius, spacing, typography } from '@/constants/tokens'

interface ConfirmDialogProps {
  visible: boolean
  title: string
  message: string
  confirmLabel: string
  icon?: keyof typeof Ionicons.glyphMap
  isLoading?: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function ConfirmDialog({
  visible,
  title,
  message,
  confirmLabel,
  icon = 'trash-outline',
  isLoading = false,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  const { semantic } = useTheme()

  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onCancel}>
      <View style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onCancel} />
        <View
          style={[
            styles.dialog,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <View style={[styles.iconWrap, { backgroundColor: semantic.status.errorBg }]}>
            <Ionicons name={icon} size={22} color={semantic.status.error} />
          </View>
          <View style={styles.copy}>
            <Text style={[styles.title, { color: semantic.text.primary }]}>{title}</Text>
            <Text style={[styles.message, { color: semantic.text.secondary }]}>{message}</Text>
          </View>
          <View style={styles.actions}>
            <Button variant="outline" size="md" onPress={onCancel} isDisabled={isLoading}>
              Cancelar
            </Button>
            <Button variant="danger" size="md" onPress={onConfirm} isLoading={isLoading}>
              {confirmLabel}
            </Button>
          </View>
        </View>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  overlay: {
    alignItems: 'center',
    backgroundColor: overlay.surface.backdrop,
    flex: 1,
    justifyContent: 'center',
    padding: spacing[5],
  },
  dialog: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    maxWidth: 420,
    padding: spacing[5],
    width: '100%',
  },
  iconWrap: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  copy: { gap: spacing[2] },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  message: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.5 },
  actions: { flexDirection: 'row', gap: spacing[2], justifyContent: 'flex-end' },
})
