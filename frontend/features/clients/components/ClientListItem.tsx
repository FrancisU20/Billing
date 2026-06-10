import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { ListItemAction, ListItemMeta } from '@/components/ui/ListItemPrimitives'
import { useTheme } from '@/lib/theme-context'
import { formatDate, initials } from '@/lib/utils/format'
import { radius, sizes, spacing, typography } from '@/constants/tokens'
import { CLIENT_IDENTIFICATION_LABELS, CLIENT_PERSON_LABELS } from '../constants'
import { ClientStatusBadge } from './ClientStatusBadge'
import type { Client } from '../types'

interface ClientListItemProps {
  client: Client
  onView: () => void
  onEdit: () => void
  onDelete: () => void
}

export function ClientListItem({ client, onView, onEdit, onDelete }: ClientListItemProps) {
  const { semantic } = useTheme()
  const displayName = client.trade_name || client.legal_name
  const email = client.emails[0] ?? 'Sin email'

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
          {initials(displayName || client.identification)}
        </Text>
      </View>

      <View style={styles.main}>
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
      </View>

      <View style={styles.actions}>
        <ListItemAction icon="eye-outline" label="Ver cliente" onPress={onView} />
        <ListItemAction icon="create-outline" label="Editar cliente" onPress={onEdit} />
        <ListItemAction icon="trash-outline" label="Eliminar cliente" danger onPress={onDelete} />
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
  avatarText: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  main: { flex: 1, minWidth: 0, gap: spacing[1] },
  nameRow: { alignItems: 'center', flexDirection: 'row', gap: spacing[2] },
  name: { flex: 1, fontSize: typography.size.base, fontWeight: typography.weight.bold },
  legalName: { fontSize: typography.size.sm },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  actions: { flexDirection: 'row', gap: spacing[2] },
})
