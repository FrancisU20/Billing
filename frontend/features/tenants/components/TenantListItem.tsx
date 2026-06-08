import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { formatDate, formatRuc, initials } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
import { TENANT_ENVIRONMENT_LABELS, TENANT_PLAN_STATUS_LABELS } from '../constants'
import { TenantStatusBadge } from './TenantStatusBadge'
import type { Tenant } from '../types'

interface TenantListItemProps {
  tenant: Tenant
  onView: () => void
  onEdit: () => void
}

export function TenantListItem({ tenant, onView, onEdit }: TenantListItemProps) {
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
        <Text style={[styles.avatarText, { color: semantic.accent.default }]}>
          {initials(tenant.trade_name)}
        </Text>
      </View>

      <View style={styles.main}>
        <View style={styles.nameRow}>
          <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
            {tenant.trade_name}
          </Text>
          <TenantStatusBadge status={tenant.status} />
        </View>
        <Text style={[styles.legalRep, { color: semantic.text.secondary }]} numberOfLines={1}>
          {tenant.legal_rep_name}
        </Text>
        <View style={styles.metaRow}>
          <MetaItem icon="card-outline" text={formatRuc(tenant.ruc)} mono />
          <MetaItem icon="cloud-outline" text={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]} />
          <MetaItem icon="pricetag-outline" text={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]} />
          <MetaItem icon="mail-outline" text={tenant.email} />
          <MetaItem icon="calendar-outline" text={formatDate(tenant.created_at)} />
        </View>
      </View>

      <View style={styles.actions}>
        <IconAction icon="eye-outline" label="Ver empresa" onPress={onView} />
        <IconAction icon="create-outline" label="Editar empresa" onPress={onEdit} />
      </View>
    </Pressable>
  )
}

function MetaItem({
  icon,
  text,
  mono = false,
}: {
  icon: keyof typeof Ionicons.glyphMap
  text: string
  mono?: boolean
}) {
  const { semantic } = useTheme()
  return (
    <View style={styles.metaItem}>
      <Ionicons name={icon} size={13} color={semantic.text.tertiary} />
      <Text
        style={[styles.metaText, mono && styles.mono, { color: semantic.text.tertiary }]}
        numberOfLines={1}
      >
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
  avatarText: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  main: { flex: 1, minWidth: 0, gap: spacing[1] },
  nameRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  name: { flex: 1, fontSize: typography.size.base, fontWeight: typography.weight.bold },
  legalRep: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  metaItem: { alignItems: 'center', flexDirection: 'row', gap: spacing[1], maxWidth: 220 },
  metaText: { fontSize: typography.size.xs },
  mono: { fontFamily: typography.fontFamily.mono },
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
