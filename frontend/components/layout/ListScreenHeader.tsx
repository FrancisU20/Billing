import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'

interface ListScreenHeaderProps {
  icon: keyof typeof Ionicons.glyphMap
  kicker: string
  heading: string
  action?: { label: string; onPress: () => void }
}

/** Encabezado compartido por las pantallas de listado: icono+kicker, titulo y boton
 * primario opcional. Cada pantalla sigue armando su propia fila de
 * metricas/filtros debajo de este componente. */
export function ListScreenHeader({ icon, kicker, heading, action }: ListScreenHeaderProps) {
  const { semantic } = useTheme()
  return (
    <View style={styles.heroRow}>
      <View style={styles.heroCopy}>
        <View style={styles.kickerRow}>
          <Ionicons name={icon} size={16} color={semantic.accent.default} />
          <Text style={[styles.kicker, { color: semantic.accent.default }]}>{kicker}</Text>
        </View>
        <Text style={[styles.heading, { color: semantic.text.primary }]}>{heading}</Text>
      </View>
      {action ? (
        <View style={styles.actions}>
          <Button variant="primary" size="md" onPress={action.onPress}>
            {action.label}
          </Button>
        </View>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  heroRow: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[4],
    justifyContent: 'space-between',
  },
  heroCopy: { flex: 1, minWidth: 260, gap: spacing[1] },
  actions: { flexDirection: 'row', gap: spacing[2] },
  kickerRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[1] },
  kicker: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    textTransform: 'uppercase',
  },
  heading: {
    fontSize: typography.size['2xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['2xl'] * 1.2,
  },
})
