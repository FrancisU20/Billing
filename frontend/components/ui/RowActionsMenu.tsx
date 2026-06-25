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
  /** Si es true, la accion se muestra atenuada y no responde a tap/click. */
  disabled?: boolean
  /** Motivo mostrado debajo del label cuando `disabled` es true — comunica por que. */
  disabledReason?: string
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
            {actions.map((action) => {
              const isDisabled = Boolean(action.disabled)
              const contentColor = isDisabled
                ? semantic.text.tertiary
                : action.danger
                  ? semantic.status.error
                  : semantic.text.secondary

              return (
                <Pressable
                  key={action.key}
                  accessibilityRole="button"
                  accessibilityLabel={action.label}
                  accessibilityState={{ disabled: isDisabled }}
                  disabled={isDisabled}
                  onPress={() => {
                    setVisible(false)
                    action.onPress()
                  }}
                  style={({ pressed }) => [
                    styles.row,
                    {
                      backgroundColor:
                        pressed && !isDisabled ? semantic.bg.secondary : 'transparent',
                    },
                  ]}
                >
                  <Ionicons name={action.icon} size={19} color={contentColor} />
                  <View style={styles.labelGroup}>
                    <Text
                      style={[
                        styles.label,
                        {
                          color: isDisabled
                            ? semantic.text.tertiary
                            : action.danger
                              ? semantic.status.error
                              : semantic.text.primary,
                        },
                      ]}
                    >
                      {action.label}
                    </Text>
                    {isDisabled && action.disabledReason ? (
                      <Text style={[styles.reason, { color: semantic.text.tertiary }]}>
                        {action.disabledReason}
                      </Text>
                    ) : null}
                  </View>
                </Pressable>
              )
            })}
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
    paddingVertical: spacing[2],
  },
  labelGroup: { flex: 1, gap: 2 },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  reason: { fontSize: typography.size.xs, lineHeight: typography.size.xs * 1.4 },
})
