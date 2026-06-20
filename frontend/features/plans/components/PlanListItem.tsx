import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Badge } from '@/components/ui/Badge'
import { ListItemAction, ListItemMeta } from '@/components/ui/ListItemPrimitives'
import { RowActionsMenu, type RowAction } from '@/components/ui/RowActionsMenu'
import { useTheme } from '@/lib/theme-context'
import { formatDate } from '@/lib/utils/format'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { cycleLabel, formatBillingPrice, formatDocumentLimit, formatPlanLimit } from '../format'
import type { Plan } from '../types'

interface PlanListItemProps {
  plan: Plan
  onView: () => void
  onEdit: () => void
  onToggle: () => void
}

export function PlanListItem({ plan, onView, onEdit, onToggle }: PlanListItemProps) {
  const { semantic } = useTheme()

  const rowActions: RowAction[] = [
    { key: 'edit', icon: 'create-outline', label: 'Editar plan', onPress: onEdit },
    {
      key: 'toggle',
      icon: plan.active ? 'pause-circle-outline' : 'play-circle-outline',
      label: plan.active ? 'Desactivar plan' : 'Activar plan',
      danger: plan.active,
      onPress: onToggle,
    },
  ]

  return (
    <Pressable
      onPress={onView}
      style={({ pressed }) => [
        styles.container,
        {
          backgroundColor: pressed ? semantic.bg.secondary : semantic.bg.card,
          borderColor: semantic.border.default,
        },
      ]}
    >
      <View style={[styles.avatar, { backgroundColor: semantic.accent.subtle }]}>
        <Ionicons name="pricetag-outline" size={20} color={semantic.accent.default} />
      </View>

      <View style={styles.main}>
        <View style={styles.nameRow}>
          <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
            {plan.name}
          </Text>
          <Badge
            label={plan.active ? 'Activo' : 'Inactivo'}
            variant={plan.active ? 'success' : 'neutral'}
            size="sm"
          />
        </View>
        <Text style={[styles.description, { color: semantic.text.secondary }]} numberOfLines={1}>
          {plan.description || plan.slug}
        </Text>
        <View style={styles.metaRow}>
          <ListItemMeta icon="cash-outline" text={formatBillingPrice(plan)} />
          <ListItemMeta icon="document-text-outline" text={formatDocumentLimit(plan)} />
          <ListItemMeta
            icon="people-outline"
            text={formatPlanLimit(plan.max_users, 'usuario', 'usuarios')}
          />
          <ListItemMeta icon="calendar-outline" text={cycleLabel(plan.limit_cycle)} />
          <ListItemMeta icon="time-outline" text={formatDate(plan.created_at)} />
        </View>
      </View>

      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver plan" onPress={onView} />
        <RowActionsMenu actions={rowActions} triggerLabel="Más acciones de plan" />
      </View>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    padding: spacing[4],
  },
  avatar: {
    alignItems: 'center',
    borderRadius: radius.md,
    height: sizes.avatarSm,
    justifyContent: 'center',
    width: sizes.avatarSm,
  },
  main: { flex: 1, gap: spacing[1], minWidth: 0 },
  nameRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  name: { flex: 1, fontSize: typography.size.base, fontWeight: typography.weight.bold },
  description: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { flexDirection: 'row', gap: spacing[2] },
})
