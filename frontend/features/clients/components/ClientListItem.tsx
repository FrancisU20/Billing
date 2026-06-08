import React from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { formatDate, initials } from '@/lib/utils/format'
import { radius, spacing, typography } from '@/constants/tokens'
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
          <MetaItem
            icon="card-outline"
            text={`${CLIENT_IDENTIFICATION_LABELS[client.identification_type]} ${client.identification}`}
            mono
          />
          <MetaItem icon="people-outline" text={CLIENT_PERSON_LABELS[client.person_type]} />
          <MetaItem icon="mail-outline" text={email} />
          <MetaItem icon="calendar-outline" text={formatDate(client.created_at)} />
        </View>
      </View>

      <View style={styles.actions}>
        <IconAction icon="eye-outline" label="Ver cliente" onPress={onView} />
        <IconAction icon="create-outline" label="Editar cliente" onPress={onEdit} />
        <IconAction icon="trash-outline" label="Eliminar cliente" danger onPress={onDelete} />
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
  legalName: { fontSize: typography.size.sm },
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
