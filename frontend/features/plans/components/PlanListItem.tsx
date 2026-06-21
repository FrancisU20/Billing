import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Badge } from '@/components/ui/Badge'
import {
  EntityAvatar,
  ListCell,
  ListItemAction,
  ListItemMeta,
} from '@/components/ui/ListItemPrimitives'
import { RowActionsMenu, type RowAction } from '@/components/ui/RowActionsMenu'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
import { useTheme } from '@/lib/theme-context'
import { formatDate } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
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
  const isDesktop = useIsDesktopLayout()

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
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <EntityAvatar icon="pricetag-outline" />

      <View style={styles.main}>
        {isDesktop ? <DesktopRow plan={plan} /> : <MobileRow plan={plan} />}
      </View>

      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver plan" onPress={onView} />
        <RowActionsMenu actions={rowActions} triggerLabel="Más acciones de plan" />
      </View>
    </View>
  )
}

function MobileRow({ plan }: { plan: Plan }) {
  const { semantic } = useTheme()
  return (
    <>
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
    </>
  )
}

function DesktopRow({ plan }: { plan: Plan }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.desktopRow}>
      <View style={styles.colPlan}>
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
      </View>
      <ListCell label="Precio" value={formatBillingPrice(plan)} style={styles.colPrice} />
      <ListCell label="Documentos" value={formatDocumentLimit(plan)} style={styles.colDocLimit} />
      <ListCell
        label="Usuarios"
        value={formatPlanLimit(plan.max_users, 'usuario', 'usuarios')}
        style={styles.colUserLimit}
      />
      <ListCell label="Ciclo" value={cycleLabel(plan.limit_cycle)} style={styles.colCycle} />
      <ListCell label="Creado" value={formatDate(plan.created_at)} style={styles.colDate} />
    </View>
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
  main: { flex: 1, gap: spacing[1], minWidth: 0 },
  nameRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  name: { flex: 1, fontSize: typography.size.base, fontWeight: typography.weight.bold },
  description: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { flexDirection: 'row', gap: spacing[2] },
  desktopRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[5] },
  colPlan: { flexBasis: 220, gap: spacing[1], minWidth: 180 },
  colPrice: { flexBasis: 110 },
  colDocLimit: { flexBasis: 120 },
  colUserLimit: { flexBasis: 110 },
  colCycle: { flex: 1, minWidth: 100 },
  colDate: { flexBasis: 110 },
})
