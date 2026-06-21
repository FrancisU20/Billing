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
import { formatDate, initials } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
import { CLIENT_IDENTIFICATION_LABELS, CLIENT_PERSON_LABELS } from '../constants'
import { ClientStatusBadge } from './ClientStatusBadge'
import type { Client } from '../types'

interface ClientListItemProps {
  client: Client
  canManage: boolean
  onView: () => void
  onEdit: () => void
  onDelete: () => void
  onToggleStatus: () => void
}

export function ClientListItem({
  client,
  canManage,
  onView,
  onEdit,
  onDelete,
  onToggleStatus,
}: ClientListItemProps) {
  const { semantic } = useTheme()
  const isDesktop = useIsDesktopLayout()
  const displayName = client.trade_name || client.legal_name
  const email = client.emails[0] ?? 'Sin email'

  const rowActions: RowAction[] = canManage
    ? [
        { key: 'edit', icon: 'create-outline', label: 'Editar cliente', onPress: onEdit },
        client.status === 'active'
          ? {
              key: 'delete',
              icon: 'trash-outline',
              label: 'Eliminar cliente',
              danger: true,
              onPress: onDelete,
            }
          : {
              key: 'activate',
              icon: 'play-circle-outline',
              label: 'Activar cliente',
              onPress: onToggleStatus,
            },
      ]
    : []

  return (
    <View
      style={[
        styles.container,
        { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
      ]}
    >
      <EntityAvatar initials={initials(displayName || client.identification)} />

      <View style={styles.main}>
        {isDesktop ? (
          <DesktopRow client={client} displayName={displayName} email={email} />
        ) : (
          <MobileRow client={client} displayName={displayName} email={email} />
        )}
      </View>

      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver cliente" onPress={onView} />
        <RowActionsMenu actions={rowActions} triggerLabel="Más acciones de cliente" />
      </View>
    </View>
  )
}

function MobileRow({
  client,
  displayName,
  email,
}: {
  client: Client
  displayName: string
  email: string
}) {
  const { semantic } = useTheme()
  return (
    <>
      <View style={styles.nameRow}>
        <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
          {displayName}
        </Text>
        <ClientStatusBadge status={client.status} />
      </View>
      <Text style={[styles.legalName, { color: semantic.text.secondary }]} numberOfLines={1}>
        {client.legal_name}
      </Text>
      <View style={styles.metaRow}>
        <ListItemMeta
          icon="card-outline"
          text={`${CLIENT_IDENTIFICATION_LABELS[client.identification_type]} ${client.identification}`}
          mono
        />
        <ListItemMeta icon="people-outline" text={CLIENT_PERSON_LABELS[client.person_type]} />
        <ListItemMeta icon="mail-outline" text={email} />
        <ListItemMeta icon="calendar-outline" text={formatDate(client.created_at)} />
      </View>
    </>
  )
}

function DesktopRow({
  client,
  displayName,
  email,
}: {
  client: Client
  displayName: string
  email: string
}) {
  const { semantic } = useTheme()
  return (
    <View style={styles.desktopRow}>
      <View style={styles.colClient}>
        <View style={styles.nameRow}>
          <Text style={[styles.name, { color: semantic.text.primary }]} numberOfLines={1}>
            {displayName}
          </Text>
          <ClientStatusBadge status={client.status} />
        </View>
        <Text style={[styles.legalName, { color: semantic.text.secondary }]} numberOfLines={1}>
          {client.legal_name}
        </Text>
      </View>
      <ListCell
        label="Identificación"
        value={`${CLIENT_IDENTIFICATION_LABELS[client.identification_type]} ${client.identification}`}
        mono
        style={styles.colIdentification}
      />
      <ListCell
        label="Tipo"
        value={CLIENT_PERSON_LABELS[client.person_type]}
        style={styles.colPerson}
      />
      <ListCell label="Email" value={email} style={styles.colEmail} />
      <ListCell label="Creado" value={formatDate(client.created_at)} style={styles.colDate} />
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
  legalName: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { flexDirection: 'row', gap: spacing[2] },
  desktopRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[5] },
  colClient: { flexBasis: 240, gap: spacing[1], minWidth: 200 },
  colIdentification: { flexBasis: 170 },
  colPerson: { flexBasis: 110 },
  colEmail: { flex: 1, minWidth: 160 },
  colDate: { flexBasis: 110 },
})
