import React, { useState } from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ListItemAction } from '@/components/ui/ListItemPrimitives'
import { useTheme } from '@/lib/theme-context'
import { overlay, radius, spacing, typography } from '@/constants/tokens'

export interface RowAction {
  key: string
  icon: keyof typeof Ionicons.glyphMap
  label: string
  danger?: boolean
  onPress: () => void
}

interface RowActionsMenuProps {
  actions: RowAction[]
  triggerLabel?: string
}

/**
 * Boton "..." que abre un action sheet con las acciones secundarias de una fila de
 * listado (todo menos "Ver", que es un boton de ojo visible aparte — la fila ya no es
 * clickeable completa, ver DocumentListItem/ClientListItem). Evita que cada fila
 * acumule 3+ botones planos.
 */
export function RowActionsMenu({ actions, triggerLabel = 'Más acciones' }: RowActionsMenuProps) {
  const [visible, setVisible] = useState(false)
  const { semantic } = useTheme()

  if (actions.length === 0) return null

  return (
    <>
      <ListItemAction
        icon="ellipsis-vertical"
        label={triggerLabel}
        onPress={() => setVisible(true)}
      />
      <Modal
        transparent
        visible={visible}
        animationType="fade"
        onRequestClose={() => setVisible(false)}
      >
        <View style={styles.overlay}>
          <Pressable style={StyleSheet.absoluteFill} onPress={() => setVisible(false)} />
          <View
            style={[
              styles.sheet,
              { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
            ]}
          >
            {actions.map((action) => (
              <Pressable
                key={action.key}
                accessibilityRole="button"
                accessibilityLabel={action.label}
                onPress={() => {
                  setVisible(false)
                  action.onPress()
                }}
                style={({ pressed }) => [
                  styles.row,
                  { backgroundColor: pressed ? semantic.bg.secondary : 'transparent' },
                ]}
              >
                <Ionicons
                  name={action.icon}
                  size={19}
                  color={action.danger ? semantic.status.error : semantic.text.secondary}
                />
                <Text
                  style={[
                    styles.label,
                    { color: action.danger ? semantic.status.error : semantic.text.primary },
                  ]}
                >
                  {action.label}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      </Modal>
    </>
  )
}

const styles = StyleSheet.create({
  overlay: {
    backgroundColor: overlay.surface.backdrop,
    flex: 1,
    justifyContent: 'flex-end',
  },
  sheet: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[1],
    margin: spacing[4],
    padding: spacing[2],
  },
  row: {
    alignItems: 'center',
    borderRadius: radius.sm,
    flexDirection: 'row',
    gap: spacing[3],
    minHeight: 48,
    paddingHorizontal: spacing[3],
  },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
})
