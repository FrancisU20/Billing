import React from 'react'
import { StyleSheet, Text, View } from 'react-native'
import {
  EntityAvatar,
  ListCell,
  ListItemAction,
  ListItemMeta,
} from '@/components/ui/ListItemPrimitives'
import { RowActionsMenu, type RowAction } from '@/components/ui/RowActionsMenu'
import { useIsDesktopLayout } from '@/lib/hooks/useIsDesktopLayout'
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
  onToggleStatus: () => void
}

export function TenantListItem({ tenant, onView, onEdit, onToggleStatus }: TenantListItemProps) {
  const { semantic } = useTheme()
  const isDesktop = useIsDesktopLayout()
  const isActive = tenant.status === 'active'

  const rowActions: RowAction[] = [
    { key: 'edit', icon: 'create-outline', label: 'Editar empresa', onPress: onEdit },
    {
      key: 'toggle',
      icon: isActive ? 'pause-circle-outline' : 'play-circle-outline',
      label: isActive ? 'Suspender empresa' : 'Reactivar empresa',
      danger: isActive,
      onPress: onToggleStatus,
    },
  ]

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <EntityAvatar initials={initials(tenant.trade_name)} />

      <View style={styles.main}>
        {isDesktop ? <DesktopRow tenant={tenant} /> : <MobileRow tenant={tenant} />}
      </View>

      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver empresa" onPress={onView} />
        <RowActionsMenu actions={rowActions} triggerLabel="Más acciones de empresa" />
      </View>
    </View>
  )
}

function MobileRow({ tenant }: { tenant: Tenant }) {
  const { semantic } = useTheme()
  return (
    <>
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
        <ListItemMeta icon="card-outline" text={formatRuc(tenant.ruc)} mono />
        <ListItemMeta
          icon="cloud-outline"
          text={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]}
        />
        <ListItemMeta
          icon="pricetag-outline"
          text={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]}
        />
        <ListItemMeta icon="mail-outline" text={tenant.email} />
        <ListItemMeta icon="calendar-outline" text={formatDate(tenant.created_at)} />
      </View>
    </>
  )
}

function DesktopRow({ tenant }: { tenant: Tenant }) {
  const { semantic } = useTheme()
  return (
    <View style={styles.desktopRow}>
      <View style={styles.colTenant}>
        <View style={styles.nameRow}>
          <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
            {tenant.trade_name}
          </Text>
          <TenantStatusBadge status={tenant.status} />
        </View>
        <Text style={[styles.legalRep, { color: semantic.text.secondary }]} numberOfLines={1}>
          {tenant.legal_rep_name}
        </Text>
      </View>
      <ListCell label="RUC" value={formatRuc(tenant.ruc)} mono style={styles.colRuc} />
      <ListCell
        label="Ambiente"
        value={TENANT_ENVIRONMENT_LABELS[tenant.sri_environment]}
        style={styles.colEnvironment}
      />
      <ListCell
        label="Plan"
        value={TENANT_PLAN_STATUS_LABELS[tenant.plan_status]}
        style={styles.colPlan}
      />
      <ListCell label="Email" value={tenant.email} style={styles.colEmail} />
      <ListCell label="Creado" value={formatDate(tenant.created_at)} style={styles.colDate} />
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
  main: { flex: 1, minWidth: 0, gap: spacing[1] },
  nameRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  name: { flex: 1, fontSize: typography.size.base, fontWeight: typography.weight.bold },
  legalRep: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { flexDirection: 'row', gap: spacing[2] },
  desktopRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[5] },
  colTenant: { flexBasis: 230, gap: spacing[1], minWidth: 200 },
  colRuc: { flexBasis: 130 },
  colEnvironment: { flexBasis: 100 },
  colPlan: { flexBasis: 110 },
  colEmail: { flex: 1, minWidth: 160 },
  colDate: { flexBasis: 110 },
})
