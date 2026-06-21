import React from 'react'
import { Modal, StyleSheet, Text, View } from 'react-native'
import { LoadingLogo } from '@/components/branding/LoadingScreen'
import { overlay, radius, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'

interface BlockingLoadingOverlayProps {
  visible: boolean
  label: string
  detail?: string
}

export function BlockingLoadingOverlay({ visible, label, detail }: BlockingLoadingOverlayProps) {
  const { semantic } = useTheme()

  return (
    <Modal
      transparent
      visible={visible}
      animationType="fade"
      onRequestClose={() => undefined}
      statusBarTranslucent
    >
      <View
        style={styles.overlay}
        accessibilityRole="progressbar"
        accessibilityViewIsModal
        accessibilityLabel={label}
      >
        <View
          style={[
            styles.panel,
            { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
          ]}
        >
          <LoadingLogo size={68} />
          <View style={styles.copy}>
            <Text style={[styles.label, { color: semantic.text.primary }]}>{label}</Text>
            {detail ? (
              <Text style={[styles.detail, { color: semantic.text.secondary }]}>{detail}</Text>
            ) : null}
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
  panel: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    maxWidth: 360,
    padding: spacing[6],
    width: '100%',
  },
  copy: { alignItems: 'center', gap: spacing[2] },
  label: { fontSize: typography.size.md, fontWeight: typography.weight.bold, textAlign: 'center' },
  detail: {
    fontSize: typography.size.sm,
    lineHeight: typography.size.sm * typography.lineHeight.normal,
    textAlign: 'center',
  },
})
