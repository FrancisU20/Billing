import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Badge } from '@/components/ui/Badge'
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
          <MetaItem icon="cash-outline" text={formatBillingPrice(plan)} />
          <MetaItem icon="document-text-outline" text={formatDocumentLimit(plan)} />
          <MetaItem
            icon="people-outline"
            text={formatPlanLimit(plan.max_users, 'usuario', 'usuarios')}
          />
          <MetaItem icon="calendar-outline" text={cycleLabel(plan.limit_cycle)} />
          <MetaItem icon="time-outline" text={formatDate(plan.created_at)} />
        </View>
      </View>

      <View style={styles.actions}>
        <IconAction icon="eye-outline" label="Ver plan" onPress={onView} />
        <IconAction icon="create-outline" label="Editar plan" onPress={onEdit} />
        <IconAction
          icon={plan.active ? 'pause-circle-outline' : 'play-circle-outline'}
          label={plan.active ? 'Desactivar plan' : 'Activar plan'}
          danger={plan.active}
          onPress={onToggle}
        />
      </View>
    </Pressable>
  )
}

function MetaItem({ icon, text }: { icon: keyof typeof Ionicons.glyphMap; text: string }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.metaItem}>
      <Ionicons name={icon} size={13} color={semantic.text.tertiary} />
      <Text style={[styles.metaText, { color: semantic.text.tertiary }]} numberOfLines={1}>
        {text}
      </Text>
    </View>
  )
}

function IconAction({
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
    height: 46,
    justifyContent: 'center',
    width: 46,
  },
  main: { flex: 1, gap: spacing[1], minWidth: 0 },
  nameRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  name: { flex: 1, fontSize: typography.size.base, fontWeight: typography.weight.bold },
  description: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  metaItem: { alignItems: 'center', flexDirection: 'row', gap: spacing[1], maxWidth: 220 },
  metaText: { fontSize: typography.size.xs },
  actions: { flexDirection: 'row', gap: spacing[2] },
  actionButton: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    height: 36,
    justifyContent: 'center',
    width: 36,
  },
})
